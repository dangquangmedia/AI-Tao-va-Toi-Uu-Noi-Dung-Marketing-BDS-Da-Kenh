# Đánh giá retrieval R1 / R2 trên gold query

> Dataset `dataset_v1` · 72 query · top-k = 10 · embedding `BAAI/bge-m3`. Sinh bằng `python -m app.dataset_cli --eval`.

## Tổng hợp

| Cấu hình | project precision@k | listing recall@k | hit@k | MRR |
|---|---:|---:|---:|---:|
| R1-fts | 0.087 | 0.117 | 0.403 | 0.127 |
| R1-vector | 0.850 | 0.855 | 0.986 | 0.921 |
| R1-hybrid | 0.551 | 0.743 | 0.972 | 0.817 |
| R2-graph | 0.686 | 0.862 | 0.917 | 0.889 |

## Theo nhóm câu hỏi (project precision@k)

| Nhóm | R1-fts | R1-vector | R1-hybrid | R2-graph |
|---|---:|---:|---:|---:|
| compare (n=12) | 0.025 | 0.408 | 0.242 | 0.183 |
| conflict (n=12) | 0.042 | 0.925 | 0.533 | 0.792 |
| fact (n=12) | 0.067 | 0.950 | 0.625 | 0.817 |
| one_hop (n=12) | 0.208 | 0.942 | 0.675 | 0.833 |
| temporal (n=12) | 0.050 | 0.983 | 0.592 | 0.817 |
| two_hop (n=12) | 0.133 | 0.892 | 0.642 | 0.675 |
