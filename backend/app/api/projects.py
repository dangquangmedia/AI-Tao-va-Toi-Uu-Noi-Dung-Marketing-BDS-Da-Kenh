from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user, require_roles
from app.models import Project, User
from app.schemas import ProjectIn, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _get_owned(project_id: str, user: User, db: Session) -> Project:
    project = db.get(Project, project_id)
    # Tenant isolation: project của tenant khác trả 404, không lộ sự tồn tại
    if project is None or project.tenant_id != user.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy dự án")
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(Project).where(Project.tenant_id == user.tenant_id).order_by(Project.created_at.desc())
    ).all()


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectIn,
    user: User = Depends(require_roles("admin", "marketer")),
    db: Session = Depends(get_db),
):
    exists = db.scalar(
        select(Project).where(Project.tenant_id == user.tenant_id, Project.slug == body.slug)
    )
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Slug đã tồn tại trong tenant")
    project = Project(
        tenant_id=user.tenant_id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        created_by=user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _get_owned(project_id, user, db)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    body: ProjectUpdate,
    user: User = Depends(require_roles("admin", "marketer")),
    db: Session = Depends(get_db),
):
    project = _get_owned(project_id, user, db)
    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    project = _get_owned(project_id, user, db)
    db.delete(project)
    db.commit()
