# Kế hoạch deep research cho đồ án AI Tạo và Tối Ưu Nội Dung Marketing BĐS Đa Kênh

## Nhận định tổng thể và cách định vị đề tài

Đề tài **“AI Tạo & Tối Ưu Nội Dung Marketing BĐS Đa Kênh”** là một hướng rất hợp với đồ án tốt nghiệp AI nếu bạn **định vị nó như một bài toán sinh nội dung có kiểm soát, đa phương thức, có grounding và có đánh giá thực nghiệm**, chứ không chỉ là “gọi API để viết content”. Các công trình gần đây cho thấy hướng đi này có giá trị thực tế rõ ràng: nghiên cứu **AI Realtor** cho thấy nội dung marketing BĐS được sinh bởi pipeline agentic có thể được người dùng ưa thích hơn nội dung do chuyên gia viết, trong khi vẫn giữ mức độ chính xác thực tế tương đương; còn **MarketingFM** cho thấy hệ thống RAG tạo nội dung marketing có thể cải thiện CTR, impressions và CPC trong A/B test quy mô lớn. citeturn14view0turn14view1

Nếu muốn đồ án có “chất học thuật”, bạn nên đặt trọng tâm vào ba câu hỏi nghiên cứu chính. Thứ nhất, **grounding đa nguồn** có giúp nội dung đúng fact hơn prompt-only hay không. Thứ hai, **critic–refiner loop** có giúp tăng mức độ thỏa ràng buộc như brand voice, SEO, persona fit và channel constraints hay không. Thứ ba, **điều kiện hóa theo phân khúc khách hàng** có làm tăng mức độ phù hợp và tính thuyết phục của nội dung so với bản generic hay không. Khung tư duy này bám khá sát xu hướng mới trong controllable text generation, retrieval-grounded marketing copy và iterative refinement. citeturn5search1turn14view1turn14view2

Chốt ngắn gọn: **đề tài này đủ mạnh để làm đồ án cuối khóa**, nhưng chỉ khi bạn biến nó thành một hệ thống nghiên cứu hoàn chỉnh gồm dữ liệu, pipeline xử lý, mô hình, huấn luyện/tinh chỉnh, đánh giá định lượng và một sản phẩm web deploy online. Nếu làm đúng, đây là đề tài vừa có tính ứng dụng cao vừa có câu chuyện nghiên cứu rõ ràng. citeturn14view1turn14view9turn17view3

## Cách thu hẹp phạm vi để vừa mạnh học thuật vừa làm kịp

Phiên bản **đủ mạnh để bảo vệ tốt** không nên cố “làm tất cả mọi thứ trong marketing BĐS”. Bạn nên chốt **một lõi sản phẩm rõ ràng**: từ dữ liệu dự án và ảnh dự án, hệ thống sinh ra bốn loại đầu ra chính gồm **mô tả căn hộ/listing description**, **bài social theo nền tảng**, **email nurturing**, và **landing page copy có SEO cơ bản**. Đây là phạm vi đủ rộng để chứng minh năng lực đa kênh, nhưng vẫn đủ hẹp để triển khai tốt. Nghiên cứu AI Realtor đã chứng minh listing description BĐS là một bài toán rất hợp cho grounded persuasive generation; MarketingFM và nghiên cứu về constrained copy generation chứng minh các ràng buộc marketing như keywords, tone of voice, length, topic ordering hoàn toàn có thể đóng khung thành pipeline sinh–đánh giá–refine. citeturn14view0turn14view1turn14view2

Về mặt sản phẩm, bạn nên chia thành **MVP** và **stretch goals**. MVP là web app có đăng nhập, phân quyền cơ bản, quản lý dự án/campaign, upload brief + ảnh, sinh nội dung theo kênh, chỉnh sửa, lưu version, export, và dashboard đánh giá cơ bản. Stretch goals là A/B testing dashboard, bandit-based suggestion, multilingual VN/EN, video script storyboard, và persona memory cho từng phân khúc. Việc chia tier như vậy rất quan trọng vì yêu cầu của bạn là **không được dừng ở notebook hay localhost**, nên phần deployed app phải được ưu tiên từ đầu. Cả Next.js lẫn FastAPI đều có tài liệu chính thức rất rõ về auth, session, authorization và security để bạn dựng sản phẩm web đúng chuẩn chứ không phải demo học thuật nửa vời. citeturn11view4turn11view5turn10search12

Nếu phải chọn một định vị “ăn điểm” nhất với hội đồng, mình khuyên bạn dùng câu sau: **“Đây là hệ thống multimodal, retrieval-grounded, controllable generation cho marketing BĐS đa kênh, có persona conditioning, SEO-aware generation, critic–refiner loop, và benchmark đánh giá đa tiêu chí.”** Câu này cho thấy bạn không chỉ làm app, mà còn đang giải quyết một bài toán AI có cấu trúc. citeturn5search1turn14view2turn17view1

## Dữ liệu nên lấy ở đâu và phải được tổ chức như thế nào

Phần dữ liệu là nơi quyết định đồ án của bạn có “ra chất nghiên cứu” hay không. Về nguyên tắc, bạn nên dùng **ba tầng dữ liệu**.

Tầng đầu tiên là **dữ liệu gốc của dự án BĐS**: tên dự án, vị trí, loại căn, diện tích, số phòng, tiện ích, pháp lý, bảng giá nếu được phép, USP, brand guideline, visual assets, brochure, floor plan, hình phối cảnh, hình thực tế. Với đồ án tốt nghiệp, tốt nhất là xin dữ liệu từ một dự án thật hoặc dựng **một bộ dữ liệu demo có giấy phép rõ ràng**. Đừng lấy portal thương mại về dùng bừa bãi làm training set sản phẩm nếu không kiểm soát được license và chất lượng. Với dữ liệu mở cho nghiên cứu, **Inside Airbnb** là một nguồn hữu ích vì cung cấp quarterly data, detailed listings, calendar, reviews và được cấp phép **CC BY 4.0**; tuy không phải dữ liệu “dự án BĐS bán căn hộ” đúng nghĩa, nó vẫn rất tốt để học cấu trúc listing, amenity, locality và chiến lược mô tả không gian sống. citeturn11view7

Tầng thứ hai là **dữ liệu phụ trợ cho vision và captioning**. Nếu bạn muốn huấn luyện/tinh chỉnh một thành phần mô tả ảnh, có thể dùng các bộ chuẩn như **MS COCO**, vốn là bộ dữ liệu lớn cho detection/segmentation/captioning, và **Conceptual Captions**, gồm khoảng **3.3 triệu** cặp ảnh–caption. Hai bộ này không phải dữ liệu BĐS chuyên biệt, nhưng cực kỳ hữu ích để warm-start pipeline vision-language hoặc để benchmark phương pháp captioning tổng quát trước khi thích nghi sang domain BĐS. citeturn7search11turn7search0turn7search5turn7search9

Tầng thứ ba là **dữ liệu nhãn nội bộ do bạn tự tạo**, và đây mới là phần quan trọng nhất cho thesis. Mỗi mẫu dữ liệu nên có dạng:

- `project_facts`: facts đã chuẩn hóa thành JSON  
- `image_set`: các ảnh của dự án hoặc căn hộ  
- `brand_profile`: giọng thương hiệu, từ khóa nên dùng, từ khóa cấm  
- `audience_persona`: gia đình trẻ, nhà đầu tư, người nước ngoài  
- `channel`: Facebook, TikTok script, email, landing page  
- `target_output`: nội dung chuẩn do người viết hoặc editor duyệt  
- `preference_pair`: bản A/B với nhãn “bản nào tốt hơn”  
- `compliance_tags`: cường điệu quá mức, sai fact, thiên kiến, claim nhạy cảm  
- `seo_tags`: primary keyword, secondary keywords, title/meta/H1/CTA  

Cách làm này bám sát các hướng nghiên cứu mới: LLaVA cho thấy **instruction tuning trên dữ liệu đa phương thức** là trục rất mạnh; Zillow cho thấy **synthetic data có kiểm soát theo domain/compliance** là khả thi; còn DPO cung cấp cơ sở tốt để học từ **preference pairs** thay vì chỉ học theo đáp án duy nhất. citeturn14view3turn14view9turn15view2

Một điểm cực kỳ quan trọng về mặt học thuật là **cách chia train/validation/test**. Bạn không nên random theo từng sample, vì như vậy model rất dễ “thấy cùng một dự án ở cả train và test”. Hãy chia **theo project hoặc campaign**, nghĩa là một dự án A chỉ nằm trong train, dự án B trong validation, dự án C trong test. Làm vậy mới đánh giá được năng lực tổng quát hóa sang dự án mới. Đây là chi tiết mà nhiều đồ án bỏ qua, nhưng lại rất ăn điểm khi phản biện hỏi đến. Quan điểm này cũng phù hợp với tinh thần của các benchmark nghiêm túc về controllable generation và evaluation reliability. citeturn3search3turn5search1

## Kiến trúc mô hình và chiến lược huấn luyện nên chọn

Với đề tài của bạn, kiến trúc tối ưu nhất không phải “một model làm hết”, mà là **hệ thống nhiều lớp**:

**Lớp grounding**: lưu facts dự án, brand guideline, persona rules, lịch sử campaign và content chuẩn trong một knowledge base có embedding search. Retrieval được dùng để kéo đúng fact trước khi sinh nội dung, vì chính các tài liệu về hallucination và consistency đều nhấn mạnh rằng grounding/retrieval giúp giảm phát ngôn sai và giữ hệ thống bám vào một tập thông tin cố định. Claude docs cũng khuyến nghị retrieval cho các tác vụ cần contextual consistency; OpenAI định nghĩa hallucination là các phát biểu nghe có vẻ hợp lý nhưng sai sự thật. citeturn17view1turn11view9turn8search8

**Lớp vision**: nhận ảnh dự án, ảnh nội thất, mặt bằng, phối cảnh; trích đặc trưng thị giác như view, ánh sáng, vật liệu, không gian, tính sang trọng, density of furnishings, và nếu có thể thì nhận dạng loại phòng hoặc amenity. Nếu đi hướng open-source có nghiên cứu, bạn có thể dùng **Qwen2-VL** hoặc một backbone kiểu **LLaVA/BLIP-2**. BLIP-2 hấp dẫn vì nối image encoder và LLM bằng một thành phần nhẹ, ít tham số phải train; Qwen2-VL hấp dẫn vì cơ chế dynamic resolution giúp xử lý ảnh ở nhiều độ phân giải; còn LLaVA là một nền cực tốt cho multimodal instruction tuning. citeturn14view4turn12search2turn14view3

**Lớp generator**: sinh nội dung chính theo format đích. Bạn có hai hướng triển khai:
- **Product-first**: dùng API model đa phương thức của OpenAI hoặc Claude cho inference. Cả OpenAI API lẫn Claude đều công khai hỗ trợ multimodal/vision; Claude còn có hướng dẫn cụ thể về cách gửi ảnh và khuyến nghị ảnh nên xuất hiện trước text khi prompt nếu use case cho phép. citeturn17view3turn17view0
- **Academic-first**: dùng một backbone open model 7B–8B, SFT bằng **LoRA** trên dữ liệu domain của bạn. LoRA giảm số tham số phải huấn luyện rất mạnh và có thể giảm memory requirement đáng kể, trong khi vẫn đạt chất lượng ngang hoặc hơn full fine-tune ở nhiều tác vụ; paper gốc nêu mức giảm đến **10,000 lần số tham số trainable** và **3 lần** nhu cầu bộ nhớ với ví dụ GPT-3 175B. citeturn15view0turn15view3

**Lớp critic/evaluator**: đây là điểm khác biệt giữa một app “chatbot viết content” và một đồ án AI nghiêm túc. Thay vì xuất một phát ra luôn, bạn nên có các critic độc lập kiểm tra:
- factual grounding  
- brand voice consistency  
- persona fit  
- SEO checklist  
- channel constraints  
- compliance/fairness  

Mô hình critic–refiner này được hỗ trợ khá mạnh bởi nghiên cứu **LLM-driven constrained copy generation**, nơi pipeline gồm generator, evaluator và refiner giúp tăng success rate đáng kể trên nhiều ràng buộc đồng thời. MarketingFM cũng dùng AutoEval kết hợp rule-based metrics và LLM-as-a-Judge để xấp xỉ đánh giá của human reviewers với mức agreement cao. citeturn14view2turn14view1

Về **chiến lược huấn luyện**, mình khuyên bạn đi theo ba tầng, theo đúng logic học thuật:

### Huấn luyện nền

Không pretrain từ đầu. Trong phạm vi đồ án, điều đó quá nặng và không cần thiết. Hãy bắt đầu từ một model đã instruction-tuned sẵn. Với vision-language, BLIP-2 và LLaVA cho thấy cách “nối” encoder ảnh với LLM bằng phần trainable nhẹ là một chiến lược khả thi và hiệu quả hơn rất nhiều so với training end-to-end từ đầu. citeturn14view4turn14view3

### Supervised fine-tuning

Dùng dữ liệu đã chuẩn hóa của bạn để dạy model chuyển từ đầu vào gồm facts + persona + channel + visual summary sang đầu ra content chuẩn. Nếu làm open-source, dùng **LoRA** để SFT là lựa chọn hợp lý nhất cho thesis vì vừa đúng chất nghiên cứu, vừa có thể chạy trong nguồn lực giới hạn. Nếu dùng commercial API cho product, bạn vẫn có thể coi lớp “huấn luyện học thuật” là một mô hình open-source nhỏ dùng để chạy thí nghiệm và benchmark, còn production dùng API model mạnh hơn. Cách này rất hay vì bạn vừa có **bài toán nghiên cứu tái lập được**, vừa có **sản phẩm demo mạnh**. citeturn15view0turn17view3

### Preference alignment

Sau SFT, bạn nên tạo **preference pairs** do marketer hoặc annotator chọn giữa hai bản nội dung. Sau đó dùng **DPO** để align model theo sở thích người dùng về độ thuyết phục, tone, CTA, brand fit và persona fit. DPO đặc biệt hợp với bài toán của bạn vì nó đơn giản hơn RLHF, dùng classification loss, và paper gốc nhấn mạnh nó ổn định, performant và nhẹ hơn về tính toán. citeturn15view2

Điểm mấu chốt cần nhấn mạnh trong luận văn là: **facts nên sống trong retrieval layer; style/voice/format nên được fine-tune.** Đây là một suy luận thiết kế rất vững: retrieval giúp grounding vào fact hiện hành và giảm hallucination, còn fine-tuning làm model tuân thủ phong cách, format và hành vi mong muốn. Các tài liệu về hallucination, retrieval consistency và controllable generation đều ủng hộ hướng tách vai trò như vậy. citeturn17view1turn8search8turn5search1

## Luồng chạy cốt lõi của hệ thống và kiến trúc web nên làm

Luồng chạy tốt nhất cho sản phẩm của bạn nên là một **pipeline nhiều bước có cấu trúc JSON**, không phải một prompt khổng lồ duy nhất. Claude docs nhấn mạnh việc dùng **structured outputs** hoặc ít nhất output format rõ ràng để tăng tính nhất quán; tài liệu prompt best practices của Anthropic cũng khuyên dùng cấu trúc rõ, ví dụ dùng XML/JSON và chỉ dẫn trực tiếp. citeturn17view1turn17view2

Luồng chạy nên như sau:

### Nhập liệu và chuẩn hóa

User tạo project/campaign, upload brochure, ảnh, brand guideline, persona config, keyword SEO, mô tả mục tiêu chiến dịch. Backend parse dữ liệu text, trích xuất facts vào schema chuẩn, sinh embeddings và đưa vào kho retrieval. Đối với ảnh, lớp vision sinh visual summary hoặc tags có kiểm chứng. Với floor plan, bạn có thể thêm bước OCR/parse sau, nhưng với MVP nên tập trung vào ảnh phối cảnh, ảnh nội thất và ảnh ngoại thất trước. Hướng multimodal listing hoặc image-grounded description đã được chứng minh là khả thi trong nhiều paper gần đây. citeturn17view0turn13search21turn13search18

### Lập brief nội bộ

Hệ thống tạo một **campaign brief trung gian** gồm:
- objective  
- target segment  
- brand voice  
- factual evidence  
- visual cues  
- channel requirements  
- forbidden claims  
- SEO instructions  

Đây là “bộ não có cấu trúc” của hệ thống; từ đây mới gọi generator. Nếu làm cẩn thận, bạn có thể lưu brief này làm artifact nghiên cứu để so sánh giữa prompt-only và structured-brief generation. Controllable generation literature cho thấy explicit control conditions rất quan trọng để đạt output đúng yêu cầu. citeturn5search1turn17view2

### Sinh bản nháp theo kênh

Generator tạo nháp đầu tiên cho từng kênh: listing description, Facebook post, email, landing page section, video script. Nên yêu cầu model trả về JSON có các field như `headline`, `hook`, `body`, `cta`, `keywords_used`, `claims`, `persona_rationale`. Cách này giúp evaluator hoạt động dễ hơn nhiều. Với Claude, structured outputs được khuyến nghị khi bạn cần schema conformance. citeturn17view1

### Tự động chấm và refine

Evaluator block chạy qua từng nháp:
- checker dựa trên rules  
- retriever-based fact checker  
- LLM judge cho brand/persona/persuasiveness  
- SEO checker theo checklist Google  
- image-text alignment checker nếu đầu ra dùng ảnh  

Nếu trượt, hệ thống không sinh lại từ đầu mà **refine có feedback cụ thể**. Đây chính là pattern từ paper iterative refinement: generator → evaluator → refiner cho đến khi qua ngưỡng hoặc đạt số vòng lặp tối đa. citeturn14view2

### Xuất bản, so sánh và học từ phản hồi

Sau khi bản qua ngưỡng, user duyệt, chỉnh sửa, export hoặc publish. Hệ thống lưu version history và phản hồi của user để xây preference dataset. Nếu có traffic thật, bạn có thể A/B test online; nếu chưa có traffic, bạn làm simulated A/B bằng human study hoặc bandit trên dữ liệu proxy. MarketingFM và nghiên cứu iterative refinement đều cho thấy online evaluation là cực kỳ quan trọng trong bối cảnh marketing. citeturn14view1turn14view2

Về **kiến trúc web/app**, stack của bạn hoàn toàn hợp lý nếu đi theo hướng sau. Frontend dùng **Next.js App Router**; backend dùng **FastAPI**; database dùng **Postgres + pgvector**; auth và RLS có thể dùng **Supabase** hoặc tự triển khai JWT + policies. Next.js docs phân tách rõ authentication, session management và authorization; FastAPI có tài liệu chính thức cho OAuth2/JWT; pgvector hỗ trợ exact và approximate nearest neighbor search ngay trong Postgres; Supabase docs nhấn mạnh RLS để bảo vệ dữ liệu ở cấp dòng và Auth dùng JWT tích hợp với database security. citeturn11view4turn11view5turn11view6turn10search11turn10search3

Từ yêu cầu sản phẩm tối thiểu của bạn, kiến trúc triển khai online phù hợp nhất là:
- Frontend: Next.js deploy lên một nền tảng managed  
- Backend: FastAPI deploy dạng container  
- Database: Postgres managed  
- Object storage: lưu ảnh, brochure, asset  
- Vector layer: pgvector ngay trong Postgres  
- Queue/background jobs: cho bước parse, embedding, generation, evaluations  
- Analytics: dashboard lưu outcome của từng variant  

Đây là cấu hình vừa đủ chuyên nghiệp để hội đồng thấy là “một hệ thống thật”, không phải demo localhost. citeturn10search17turn10search16turn11view6turn10search19

## Cách đánh giá khoa học để đồ án có chiều sâu

Phần đánh giá nên được thiết kế như một benchmark nhỏ của riêng bạn. Không nên chỉ chấm bằng “thấy hay”. Hãy đánh giá theo **năm trục**.

Trục đầu là **factuality/grounding**: nội dung có bám đúng fact dự án không, có thêm thông tin không có trong nguồn không, có dùng visual cues sai không. Đây là trục tối quan trọng vì hallucination là lỗi cốt lõi của LLM; OpenAI mô tả hallucination là các phát biểu nghe hợp lý nhưng sai, còn các survey về hallucination đều xem retrieval là một hướng giảm rủi ro quan trọng. citeturn11view9turn8search8turn8search13

Trục hai là **brand consistency và controllability**: output có giữ được tone thương hiệu, lexical constraints, persona cues, CTA style, keyword placement hay không. Survey về controllable text generation khẳng định đây là một vùng nghiên cứu riêng với nhiều kỹ thuật như prompt engineering, fine-tuning, RL và decoding intervention. Các tài liệu của Anthropic cũng nhấn mạnh sự cần thiết của format rõ ràng, examples và retrieval để tăng tính nhất quán. citeturn5search1turn17view2turn17view1

Trục ba là **SEO quality cho landing page**. Google Search Central nhấn mạnh rằng nội dung nên là **helpful, reliable, people-first**, dùng các từ người dùng thực sự tìm kiếm ở các vị trí nổi bật như title, heading, alt text, link text; Google cũng nói structured data giúp máy tìm kiếm hiểu rõ nội dung trang và có thể mở đường cho rich results. Vì vậy, SEO trong đồ án của bạn không nên bị hiểu là “spam keyword”, mà nên đóng khung thành một bộ constraint: title/H1 phù hợp, keyword tự nhiên, section structure hợp lý, alt text, internal links, JSON-LD nếu có schema phù hợp. citeturn11view1turn11view2turn11view3

Trục bốn là **multimodal alignment**: nội dung có mô tả đúng ảnh không. Với trục này, bạn có thể dùng **CLIPScore** cho image-text compatibility; paper gốc cho thấy metric này có tương quan cao với đánh giá của con người trong bài toán captioning, dù vẫn có giới hạn ở các ngữ cảnh cần nhiều knowledge ngoài ảnh. Nếu bạn có reference text chuẩn, bổ sung **BERTScore** để đo semantic similarity giữa output và reference. citeturn15view1turn14view7

Trục năm là **human preference và task success**. Đây mới là “vua” trong marketing. Bạn nên tổ chức một human study nhỏ, ví dụ 20–30 người đóng vai marketer hoặc khách hàng mục tiêu, chấm các cặp output theo các tiêu chí: hấp dẫn, đáng tin, đúng persona, đúng brand, đáng click, đáng liên hệ. Ngoài ra, có thể dùng **LLM-as-a-Judge** như một evaluator phụ, nhưng đừng xem nó là chân lý vì survey gần đây nhấn mạnh bài toán reliability, consistency và bias của cách chấm này. MarketingFM cũng cho thấy human oversight vẫn rất quan trọng dù AutoEval đã khá tốt. citeturn3search3turn14view1turn9search18

Một bộ **ablation study** hợp lý cho luận văn của bạn sẽ gồm:
- prompt-only vs RAG-grounded  
- no-vision vs with-vision  
- single-pass generation vs critic–refiner  
- generic content vs persona-conditioned content  
- no-fine-tune vs SFT-LoRA vs SFT-LoRA+DPO  

Nếu bạn làm được bộ ablation này, luận văn sẽ rất “ra dáng nghiên cứu”. Các paper gần đây trong marketing generation, iterative refinement, real-estate persuasion và controllable generation đều cho thấy những khác biệt kiến trúc kiểu này có ý nghĩa đo được. citeturn14view0turn14view1turn14view2turn15view2

Một điểm nữa không được bỏ qua là **fairness/compliance trong BĐS**. Zillow và các tác giả của “Compliant Real Estate Chatbot” cho thấy chatbot BĐS có thể vô tình tái tạo các hành vi steering/redlining hoặc trả lời theo hướng vi phạm fairness. Dù bạn làm bối cảnh Việt Nam, bài học kiến trúc vẫn giữ nguyên: cần có forbidden topics, sensitive-attribute filters, policy checker, và human review cho các claim nhạy cảm. Đây là một bonus rất mạnh khi viết chương “ethical considerations”. citeturn14view9

## Kế hoạch triển khai chi tiết theo từng giai đoạn

Cách triển khai hợp lý nhất là đi theo hướng **product-first nhưng research-complete**. Tức là bạn xây được app deploy thật ngay từ sớm, đồng thời cài từng lớp nghiên cứu vào dần. Kế hoạch khả thi cho một học kỳ có thể như sau.

### Giai đoạn khởi tạo

Trong 1–2 tuần đầu, chốt problem statement, research questions, schema dữ liệu và danh sách đầu ra hỗ trợ. Đồng thời dựng skeleton app với Next.js + FastAPI + Postgres, auth cơ bản và mô hình user/project/campaign. Điều này bám sát hướng dẫn auth và authorization của Next.js/FastAPI, và giúp bạn tránh rơi vào bẫy “nghiên cứu xong mới bắt đầu làm sản phẩm”. citeturn11view4turn11view5

### Giai đoạn dữ liệu

Trong 2–3 tuần tiếp theo, làm data pipeline:
- thu thập 1 bộ dữ liệu dự án thật hoặc bán thật có license rõ  
- chuẩn hóa thành JSON schema  
- xây brand book mẫu  
- định nghĩa persona taxonomy  
- tạo 200–500 mẫu instruction-output ban đầu  
- tạo ít nhất 100–200 preference pairs  
- xây test set tách theo project  

Nếu thiếu dữ liệu thật, dùng chiến lược “mixed dataset”: proxy listing từ Inside Airbnb cho cấu trúc listing + visual assets được phép dùng + synthetic augmentation theo prompt có kiểm duyệt. Zillow paper cho thấy synthetic domain data hoàn toàn có thể là một phần nghiêm túc của pipeline nếu bạn giới hạn và kiểm tra kỹ. citeturn11view7turn14view9

### Giai đoạn baseline

Tiếp theo, dựng ba baseline:
- baseline A: prompt-only text model  
- baseline B: RAG-grounded text model  
- baseline C: RAG-grounded + vision summary  

Chỉ riêng ba baseline này đã đủ tạo kết quả ban đầu cho báo cáo midterm. Đồng thời, chấm offline bằng factuality, BERTScore, human rubric. Việc có baseline rõ ràng từ đầu sẽ giúp mọi cải tiến sau đó có ý nghĩa khoa học, thay vì chỉ “thấy tốt hơn bằng cảm giác”. citeturn14view7turn11view9

### Giai đoạn tinh chỉnh

Nếu bạn đi theo open-source track, đây là lúc SFT bằng LoRA trên task chính. Sau đó, huấn luyện thêm DPO từ preference pairs. Nếu nguồn lực hạn chế, chỉ cần fine-tune text generator trước; phần vision có thể dùng API/web-scale VLM để sinh visual summary. LoRA và DPO chính là hai “vũ khí” hợp lý nhất để đồ án có nội dung huấn luyện thực sự mà vẫn nằm trong tầm tài nguyên sinh viên. citeturn15view0turn15view2

### Giai đoạn critic–refiner và SEO

Sau khi có generator đủ ổn, bổ sung evaluator modules:
- fact checker dựa trên retrieval  
- brand/persona judge  
- SEO rule checker  
- channel formatter  
- image-text alignment checker  

Sau đó nối thành iterative refinement loop. Đây là giai đoạn dễ cho ra improvement rõ trên bảng kết quả vì paper về constrained copy generation đã cho thấy loop này tăng success rate khá mạnh. citeturn14view2

### Giai đoạn hoàn thiện sản phẩm

Cuối kỳ, hoàn thiện dashboard, export, versioning, logs, analytics. Thêm A/B testing screen, dù chỉ là offline simulator nếu chưa có traffic thật. Đảm bảo mọi thứ deploy online, có quyền user/admin/editor, có quản lý dự án, campaign, assets và content history. Đây là phần đáp ứng trực tiếp yêu cầu đầu ra “web/app hoàn chỉnh — deployed online”. citeturn11view4turn10search3turn10search11

Nếu muốn có một **plan cực thực dụng**, mình khuyên bạn chốt như sau:

- **Bản chốt để làm đồ án**: RAG + vision summary + critic–refiner + optional LoRA fine-tune text model.  
- **Không nên cố full multimodal training từ đầu**: quá nặng, khó kịp, khó debug, ít giá trị hơn so với một hệ thống grounding tốt.  
- **Nơi đặt đóng góp học thuật**: dataset schema, persona-conditioned generation, critic–refiner loop, benchmark đa tiêu chí, và ablation study.  
- **Nơi đặt đóng góp sản phẩm**: app deployed, auth/RBAC, project management, content generation pipeline, versioning, export, dashboard.  

Từ bằng chứng của AI Realtor, MarketingFM, LoRA, DPO, BLIP-2, LLaVA, các tài liệu về SEO của Google và tài liệu chính thức của Claude/OpenAI về multimodal/consistency, đây là cấu hình có xác suất thành công cao nhất cho một đồ án AI BĐS vừa có chiều sâu vừa có demo mạnh. citeturn14view0turn14view1turn15view0turn15view2turn14view4turn14view3turn11view1turn11view2turn17view0turn17view1turn17view3

## Đề xuất chốt để bạn triển khai ngay

Nếu phải chốt một phương án duy nhất, mình sẽ khuyên bạn triển khai theo cấu hình này:

### Tên định vị học thuật

**Multimodal Retrieval-Grounded Controlled Generation for Multi-Channel Real Estate Marketing Content**

Cách đặt như vậy vừa đúng với bản chất bài toán, vừa cho phép mở rộng sang persona, SEO, brand consistency và A/B optimization. citeturn14view0turn14view1turn5search1

### Kiến trúc chốt

- **Frontend**: Next.js  
- **Backend**: FastAPI  
- **DB**: Postgres + pgvector  
- **Auth/RBAC**: JWT + RLS  
- **Generator production**: OpenAI hoặc Claude multimodal API  
- **Research model**: open 7B/8B + LoRA SFT + DPO  
- **Vision**: Qwen2-VL hoặc Claude/OpenAI vision cho image summary  
- **Evaluator**: rule-based + LLM judge + retrieval fact checker  
- **Deployment**: frontend và backend online, object storage cho ảnh/brochure  

Cấu hình này tận dụng đúng thế mạnh của stack bạn nêu ra, đồng thời phù hợp với ràng buộc “không chỉ localhost”. citeturn11view4turn11view5turn11view6turn10search11turn17view0turn17view3

### Nghiên cứu chốt

Bạn nên tập trung chứng minh ba giả thuyết:
- **RAG-grounded** tốt hơn prompt-only về factuality  
- **Vision + text grounding** tốt hơn text-only trong mô tả BĐS  
- **Critic–refiner + persona conditioning** tốt hơn single-pass generic generation về human preference và constraint satisfaction  

Ba giả thuyết này vừa đủ sâu để viết một luận văn nghiêm túc, lại vừa bám rất sát vào giá trị thực chiến của sản phẩm. citeturn14view0turn14view1turn14view2

### Deliverables chốt

Để hội đồng khó bắt bẻ, bộ deliverables nên gồm:
- Web app deployed online  
- Dataset schema + mẫu dữ liệu đã gán nhãn  
- Training/fine-tuning pipeline  
- Evaluation benchmark + ablation  
- Demo end-to-end từ upload brief đến export content  
- Báo cáo nêu rõ kiến trúc, dữ liệu, huấn luyện, đánh giá và giới hạn hệ thống  

Nếu bạn làm được trọn bộ này, đề tài không chỉ “đủ làm đồ án”, mà còn có thể nâng lên thành bài báo workshop hoặc portfolio cực mạnh cho vị trí AI Engineer / Applied AI / GenAI Product Engineer. citeturn14view1turn14view9turn17view3