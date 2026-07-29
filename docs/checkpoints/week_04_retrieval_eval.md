# Đánh giá retrieval R1 / R2 trên gold query

> Dataset `dataset_v1` · 72 query · top-k = 10 · embedding `BAAI/bge-m3`. Sinh bằng `python -m app.dataset_cli --eval`.

## Tổng hợp

| Cấu hình | project precision@k | listing recall@k | hit@k | MRR |
|---|---:|---:|---:|---:|
| R1-fts | 0.090 | 0.117 | 0.431 | 0.132 |
| R1-bm25 | 0.964 | 0.848 | 1.000 | 0.993 |
| R1-vector | 0.940 | 0.855 | 1.000 | 0.976 |
| R1-hybrid | 0.981 | 0.865 | 1.000 | 1.000 |
| R2-graph | 0.738 | 0.862 | 0.972 | 0.972 |
| R3-fixed | 0.986 | 0.928 | 1.000 | 1.000 |
| R3-router | 1.000 | 0.938 | 1.000 | 1.000 |

## Theo nhóm câu hỏi (project precision@k)

| Nhóm | R1-fts | R1-bm25 | R1-vector | R1-hybrid | R2-graph | R3-fixed | R3-router |
|---|---:|---:|---:|---:|---:|---:|---:|
| compare (n=12) | 0.042 | 0.983 | 0.950 | 0.975 | 0.492 | 0.975 | 1.000 |
| conflict (n=12) | 0.042 | 0.950 | 0.925 | 0.958 | 0.792 | 0.975 | 1.000 |
| fact (n=12) | 0.067 | 0.975 | 0.950 | 0.983 | 0.817 | 0.992 | 1.000 |
| one_hop (n=12) | 0.208 | 0.983 | 0.942 | 1.000 | 0.833 | 1.000 | 1.000 |
| temporal (n=12) | 0.050 | 0.933 | 0.983 | 1.000 | 0.817 | 1.000 | 1.000 |
| two_hop (n=12) | 0.133 | 0.958 | 0.892 | 0.967 | 0.675 | 0.975 | 1.000 |
