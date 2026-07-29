# Đánh giá retrieval R1 / R2 / R3 trên gold query

> Dataset `dataset_v1` · 108 query · top-k = 10 · embedding `BAAI/bge-m3`. Sinh bằng `python -m app.dataset_cli --eval`.

## Tổng hợp

| Cấu hình | project precision@k | listing precision@k | listing recall@k | hit@k | MRR |
|---|---:|---:|---:|---:|---:|
| R1-fts | 0.086 | 0.061 | 0.084 | 0.418 | 0.139 |
| R1-bm25 | 0.739 | 0.479 | 0.609 | 0.898 | 0.793 |
| R1-vector | 0.755 | 0.557 | 0.635 | 0.939 | 0.833 |
| R1-hybrid | 0.792 | 0.590 | 0.655 | 0.959 | 0.850 |
| R2-graph | 0.665 | 0.394 | 0.608 | 0.939 | 0.875 |
| R3-fixed | 0.797 | 0.562 | 0.697 | 0.959 | 0.855 |
| R3-router | 0.825 | 0.580 | 0.708 | 0.980 | 0.857 |

## Tách theo độ khó của câu hỏi

`standard` = câu hỏi **nêu tên dự án** (bộ Tuần 3). `hard` = câu hỏi mô tả theo thuộc tính / ngân sách / địa bàn, **không nêu tên dự án** (bộ Tuần 6). Chênh lệch giữa hai cột là phần precision đến từ khớp tên chứ không từ tìm kiếm.

| Cấu hình | hard: proj.prec | hard: recall | hard: MRR | standard: proj.prec | standard: recall | standard: MRR |
|---|---:|---:|---:|---:|---:|---:|
| R1-fts | 0.073 | 0.015 | 0.160 | 0.090 | 0.117 | 0.132 |
| R1-bm25 | 0.115 | 0.130 | 0.240 | 0.964 | 0.848 | 0.993 |
| R1-vector | 0.242 | 0.194 | 0.438 | 0.940 | 0.855 | 0.976 |
| R1-hybrid | 0.269 | 0.235 | 0.435 | 0.981 | 0.865 | 1.000 |
| R2-graph | 0.465 | 0.101 | 0.608 | 0.738 | 0.862 | 0.972 |
| R3-fixed | 0.273 | 0.235 | 0.453 | 0.986 | 0.928 | 1.000 |
| R3-router | 0.339 | 0.248 | 0.462 | 1.000 | 0.938 | 1.000 |

Số câu mỗi bộ: hard n=36, standard n=72.

## Theo nhóm câu hỏi (project precision@k)

| Nhóm | R1-fts | R1-bm25 | R1-vector | R1-hybrid | R2-graph | R3-fixed | R3-router |
|---|---:|---:|---:|---:|---:|---:|---:|
| compare (n=12) | 0.042 | 0.983 | 0.950 | 0.975 | 0.492 | 0.975 | 1.000 |
| conflict (n=12) | 0.042 | 0.950 | 0.925 | 0.958 | 0.792 | 0.975 | 1.000 |
| fact (n=12) | 0.067 | 0.975 | 0.950 | 0.983 | 0.817 | 0.992 | 1.000 |
| hard_attribute (n=12) | 0.030 | 0.160 | 0.240 | 0.250 | 0.180 | 0.250 | 0.320 |
| hard_budget (n=12) | 0.000 | 0.140 | 0.140 | 0.180 | 0.180 | 0.180 | 0.220 |
| hard_location (n=12) | 0.145 | 0.064 | 0.291 | 0.327 | 0.855 | 0.336 | 0.409 |
| one_hop (n=12) | 0.208 | 0.983 | 0.942 | 1.000 | 0.833 | 1.000 | 1.000 |
| temporal (n=12) | 0.050 | 0.933 | 0.983 | 1.000 | 0.817 | 1.000 | 1.000 |
| two_hop (n=12) | 0.133 | 0.958 | 0.892 | 0.967 | 0.675 | 0.975 | 1.000 |

## Theo nhóm câu hỏi (listing precision@k chuẩn hóa theo trần)

Chia cho trần `min(1, số đáp án đúng / k)` — cột này mới so sánh được giữa các nhóm có số đáp án chênh nhau. Nhóm nêu tên dự án thường chỉ có vài tin đúng nên precision thô luôn thấp dù hệ thống trả về đúng hết.

| Nhóm | số đáp án TB | R1-fts | R1-bm25 | R1-vector | R1-hybrid | R2-graph | R3-fixed | R3-router |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| compare | 10.7 | 0.070 | 0.986 | 0.964 | 0.972 | 0.694 | 0.972 | 1.000 |
| conflict | 3.3 | 0.017 | 0.988 | 0.983 | 0.983 | 0.948 | 1.000 | 1.000 |
| fact | 2.8 | 0.028 | 0.986 | 0.986 | 0.956 | 0.923 | 1.000 | 1.000 |
| hard_attribute | 7.4 | 0.008 | 0.236 | 0.339 | 0.386 | 0.118 | 0.386 | 0.416 |
| hard_budget | 11.8 | 0.008 | 0.160 | 0.215 | 0.296 | 0.034 | 0.296 | 0.300 |
| hard_location | 41.2 | 0.147 | 0.117 | 0.492 | 0.536 | 0.725 | 0.535 | 0.618 |
| one_hop | 9.2 | 0.229 | 0.976 | 0.932 | 1.000 | 1.000 | 1.000 | 1.000 |
| temporal | 5.8 | 0.043 | 0.791 | 0.939 | 0.960 | 0.937 | 0.986 | 1.000 |
| two_hop | 3.5 | 0.356 | 1.000 | 1.000 | 1.000 | 0.833 | 1.000 | 1.000 |

## Sweep trọng số cho câu hỏi mô tả (bộ hard)

Bảng xếp theo project precision, nhưng **quyết định không lấy dòng đầu**: tăng trọng số graph lên 1,5 đẩy project precision lên cao nhất trong khi *listing recall sụt gần một nửa* — nhánh graph kéo về đúng dự án nhưng không đúng tin, và còn chiếm chỗ của hai nhánh văn bản. Khâu sinh nội dung cần đúng **tin** để lấy fact, nên trọng số chốt theo listing precision/recall.

| vector | bm25 | graph | project precision@k | listing precision@k | listing recall@k | MRR |
|---:|---:|---:|---:|---:|---:|---:|
| 1.0 | 0.3 | 1.5 | 0.492 | 0.333 | 0.132 | 0.688 |
| 1.0 | 0.1 | 2.0 | 0.473 | 0.319 | 0.120 | 0.605 |
| 0.6 | 0.1 | 2.0 | 0.473 | 0.319 | 0.120 | 0.605 |
| 1.0 | 0.0 | 3.0 | 0.465 | 0.308 | 0.113 | 0.611 |
| 1.0 | 0.3 | 0.9 | 0.339 | 0.387 | 0.248 | 0.462 |
| 1.0 | 0.6 | 0.3 | 0.273 | 0.350 | 0.235 | 0.453 |

Trọng số chốt cho chế độ discovery: `{'vector': 1.0, 'bm25': 0.3, 'graph': 0.9}` (listing precision 0.387, recall 0.248).
