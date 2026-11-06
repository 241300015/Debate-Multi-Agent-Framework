from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, Response, UploadFile
from fastapi.responses import Response as FastAPIResponse

from ..aigc import AigcDetectionService, AigcTaskCreated, AigcTaskSnapshot
from ..aigc.schemas import AigcAvailability
from ..services.aigc_report_generator import generate_aigc_pdf
from .dependencies import get_aigc_detection_service

router = APIRouter(prefix="/aigc", tags=["aigc-screening"])


def _authorize(
    task_id: str,
    access_code: str | None,
    service: AigcDetectionService,
) -> None:
    if not access_code or not service.repository.authorize(task_id, access_code):
        raise HTTPException(status_code=403, detail="AIGC task access code is invalid")


@router.get("/availability", response_model=AigcAvailability)
async def availability(
    service: AigcDetectionService = Depends(get_aigc_detection_service),
) -> AigcAvailability:
    return service.availability()


@router.post("/tasks", response_model=AigcTaskCreated, status_code=202)
async def create_task(
    background_tasks: BackgroundTasks,
    pdf: UploadFile = File(...),
    service: AigcDetectionService = Depends(get_aigc_detection_service),
) -> AigcTaskCreated:
    if not pdf.filename or not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    service_status = service.availability()
    if not service_status.ready:
        raise HTTPException(status_code=503, detail=service_status.message)
    created, source_path = service.allocate(pdf.filename)
    temporary_path = source_path.with_suffix(".uploading")
    size = 0
    first = b""
    try:
        with temporary_path.open("wb") as target:
            while chunk := await pdf.read(1024 * 1024):
                if not first:
                    first = chunk[:5]
                size += len(chunk)
                if size > service.max_pdf_bytes:
                    raise HTTPException(status_code=413, detail="PDF exceeds configured size limit")
                target.write(chunk)
        if not first.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF")
        temporary_path.replace(source_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        service.repository.mark_failed(created.task_id, "PDF upload failed")
        raise
    finally:
        await pdf.close()
    background_tasks.add_task(service.execute, created.task_id)
    return created


@router.get("/tasks/{task_id}", response_model=AigcTaskSnapshot)
async def get_task(
    task_id: str,
    x_aigc_access_code: str | None = Header(None, alias="X-AIGC-Access-Code"),
    service: AigcDetectionService = Depends(get_aigc_detection_service),
) -> AigcTaskSnapshot:
    _authorize(task_id, x_aigc_access_code, service)
    snapshot = service.repository.get(task_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="AIGC task does not exist")
    return snapshot


@router.get("/tasks/{task_id}/report", response_class=FastAPIResponse)
async def export_task_report(
    task_id: str,
    x_aigc_access_code: str | None = Header(None, alias="X-AIGC-Access-Code"),
    service: AigcDetectionService = Depends(get_aigc_detection_service),
) -> FastAPIResponse:
    """导出 AIGC 检测报告 PDF。"""
    _authorize(task_id, x_aigc_access_code, service)
    snapshot = service.repository.get(task_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="AIGC task does not exist")
    if snapshot.status != "succeeded" or snapshot.result is None:
        raise HTTPException(status_code=409, detail="报告尚未就绪，检测未成功完成")
    try:
        pdf_bytes = await asyncio.to_thread(
            generate_aigc_pdf, snapshot.source_filename, snapshot.result
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"生成 AIGC 报告失败: {exc}") from exc
    base = snapshot.source_filename.rsplit(".", 1)[0] or snapshot.source_filename
    filename = f"{base}_AIGC检测报告.pdf"
    from urllib.parse import quote

    return FastAPIResponse(
        content=pdf_bytes.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{quote(filename)}\"; "
                f"filename*=UTF-8''{quote(filename)}"
            ),
        },
    )


@router.post("/tasks/{task_id}/retry", response_model=AigcTaskSnapshot, status_code=202)
async def retry_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    x_aigc_access_code: str | None = Header(None, alias="X-AIGC-Access-Code"),
    service: AigcDetectionService = Depends(get_aigc_detection_service),
) -> AigcTaskSnapshot:
    _authorize(task_id, x_aigc_access_code, service)
    try:
        snapshot = service.repository.prepare_retry(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AIGC task does not exist") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    background_tasks.add_task(service.execute, task_id)
    return snapshot


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    x_aigc_access_code: str | None = Header(None, alias="X-AIGC-Access-Code"),
    service: AigcDetectionService = Depends(get_aigc_detection_service),
) -> Response:
    _authorize(task_id, x_aigc_access_code, service)
    try:
        service.delete(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AIGC task does not exist") from exc
    return Response(status_code=204)
