"""Test traversal ≤2 hop trên Property Knowledge Graph (gate Tuần 2)."""

from app.models import GraphEntity
from app.services.graph import find_entity, project_unit_paths, traverse
from app.services.pipeline import run_clean_pipeline
from tests.test_pipeline import RECORDS, databds, imported  # noqa: F401 — fixture dùng lại

assert RECORDS  # fixture dữ liệu dùng chung với test pipeline


def test_path_project_building_unittype(db, imported):  # noqa: F811
    run_clean_pipeline(db, **imported)

    result = project_unit_paths(db, imported["tenant_id"], "grand-view")

    assert result["project"]["name"] == "Grand View"
    assert result["n_via_building"] == 2  # 2PN và 3PN đều thuộc tòa S3
    assert result["n_direct"] == 2

    via_building = [p for p in result["paths"] if p["depth"] == 2]
    duong_di = [[node["name"] for node in p["nodes"]] for p in via_building]
    assert ["Grand View", "Tòa S3", "apartment-2pn"] in duong_di
    assert ["Grand View", "Tòa S3", "apartment-3pn"] in duong_di
    # Mỗi cạnh trên đường đi phải giải thích được bằng nguồn
    for path in via_building:
        assert all(edge["source_url"] for edge in path["edges"])
        assert [edge["type"] for edge in path["edges"]] == ["PART_OF", "HAS_UNIT_TYPE"]


def test_traverse_khong_vuot_qua_2_hop(db, imported):  # noqa: F811
    run_clean_pipeline(db, **imported)
    project = find_entity(db, imported["tenant_id"], "Project", "grand-view")

    một_hop = traverse(db, imported["tenant_id"], project.id, max_depth=1)
    hai_hop = traverse(db, imported["tenant_id"], project.id, max_depth=2)

    assert {p["depth"] for p in một_hop} == {1}
    assert {p["depth"] for p in hai_hop} <= {1, 2}
    assert len(hai_hop) > len(một_hop)
    # Không quay lại chính node xuất phát
    assert all(node["id"] != project.id for p in hai_hop for node in p["nodes"][1:])


def test_traverse_ton_trong_tenant(db, seeded, imported):  # noqa: F811
    run_clean_pipeline(db, **imported)
    project = find_entity(db, imported["tenant_id"], "Project", "grand-view")

    assert traverse(db, seeded["t2"].id, project.id) == []
    assert find_entity(db, seeded["t2"].id, "Project", "grand-view") is None


def test_du_an_khong_ton_tai(db, imported):  # noqa: F811
    run_clean_pipeline(db, **imported)
    assert project_unit_paths(db, imported["tenant_id"], "khong-co-du-an") == {
        "project": None,
        "paths": [],
    }


def test_node_khong_co_canh_tra_ve_rong(db, imported):  # noqa: F811
    run_clean_pipeline(db, **imported)
    orphan = GraphEntity(
        tenant_id=imported["tenant_id"], entity_type="Project", canonical_key="le-loi", name="Lẻ Loi"
    )
    db.add(orphan)
    db.flush()
    assert traverse(db, imported["tenant_id"], orphan.id) == []
