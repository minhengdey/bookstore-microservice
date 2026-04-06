# Báo cáo: Ứng dụng Trí tuệ Nhân tạo trong Thương mại Điện tử và Hệ thống Phân tích Hành vi Khách hàng để Tư vấn Dịch vụ

**Môn học / Lĩnh vực:** Hệ thống Phân tán & Trí tuệ Nhân tạo Ứng dụng  

**Phạm vi tài liệu:**  
- **Phần I:** Khảo sát tổng quan các hướng ứng dụng AI trong e-commerce (khoảng năm chương mục tương đương năm “trang” nội dung chính).  
- **Phần II:** Mô tả kiến trúc và luồng nghiệp vụ của ứng dụng *Phân tích hành vi khách hàng để tư vấn dịch vụ*, được hiện thực hóa trong một hệ microservice sách điện tử / bookstore; phần này trình bày bằng ngôn ngữ hệ thống và khái niệm, **không** yêu cầu người đọc mở mã nguồn.

---

## Tóm tắt (Abstract)

Thương mại điện tử đã vượt xa mô hình “ứng dụng web + cơ sở dữ liệu quan hệ”. Các nền tảng lớn vận hành pipeline dữ liệu thời gian thực, hệ thống khuyến nghị đa tầng, tìm kiếm đa phương thức, chatbot kết hợp mô hình ngôn ngữ lớn (LLM) và kiến trúc truy xuất tăng cường sinh (RAG), cùng các vòng lặp vận hành mô hình (MLOps). Báo cáo này, một mặt, hệ thống hóa các lớp ứng dụng AI phổ biến trong e-commerce; mặt khác, ánh xạ các ý tưởng đó vào một bài toán cụ thể: **phân tích hành vi người dùng** (xem, thêm giỏ, mua, đánh giá…) để **gợi ý sản phẩm** và **tư vấn dịch vụ** qua kênh trò chuyện, trong đó có **mô hình học sâu** mô phỏng pipeline recall–ranking–re-ranking, **cơ sở tri thức** (knowledge base) phục vụ tư vấn, **RAG** để neo câu trả lời vào dữ liệu nội bộ, và **triển khai dạng microservice** tích hợp qua cổng API. Mục tiêu của tài liệu là làm rõ *vì sao* từng thành phần tồn tại và *cách* chúng phối hợp trong một kiến trúc phân tán, phù hợp sinh viên và kỹ sư cần một bản đồ khái niệm trước khi đi sâu triển khai.

**Từ khóa:** e-commerce, hệ thống khuyến nghị, học sâu, RAG, knowledge base, microservice, phân tích hành vi.

---

## Mục lục

1. [Phần I — Khảo sát AI trong e-commerce](#phần-i--khảo-sát-ai-trong-e-commerce)  
   1.1. [Bối cảnh và động lực](#11-bối-cảnh-và-động-lực)  
   1.2. [Hệ thống khuyến nghị: từ lọc cơ bản đến pipeline đa tầng](#12-hệ-thống-khuyến-nghị-từ-lọc-cơ-bản-đến-pipeline-đa-tầng)  
   1.3. [Tìm kiếm, đa phương thức và cơ sở dữ liệu vector](#13-tìm-kiếm-đa-phương-thức-và-cơ-sở-dữ-liệu-vector)  
   1.4. [RAG và chatbot: từ quy tắc cứng đến sinh có neo](#14-rag-và-chatbot-từ-quy-tắc-cứng-đến-sinh-có-neo)  
   1.5. [Định giá động, tối ưu suy luận và MLOps](#15-định-giá-động-tối-ưu-suy-luận-và-mlops)  
   1.6. [Cold start, đa dạng, công bằng và giải thích được](#16-cold-start-đa-dạng-công-bằng-và-giải-thích-được)  
   1.7. [Computer Vision, NLP sản phẩm và kiểm duyệt nội dung](#17-computer-vision-nlp-sản-phẩm-và-kiểm-duyệt-nội-dung)  
   1.8. [Case study minh họa: Tiki, Shopee và xu hướng cloud-native](#18-case-study-minh-họa-tiki-shopee-và-xu-hướng-cloud-native)  
2. [Phần II — Ứng dụng: Phân tích hành vi & tư vấn dịch vụ](#phần-ii--ứng-dụng-phân-tích-hành-vi--tư-vấn-dịch-vụ)  
   2.1. [Vị trí bài toán trong hệ e-commerce](#21-vị-trí-bài-toán-trong-hệ-e-commerce)  
   2.2. [Mô hình học sâu cho hành vi (pipeline ba giai đoạn)](#22-mô-hình-học-sâu-cho-hành-vi-pipeline-ba-giai-đoạn)  
   2.3. [Knowledge base phục vụ tư vấn](#23-knowledge-base-phục-vụ-tư-vấn)  
   2.4. [RAG: truy xuất lai, chống ảo giác, đa lượt](#24-rag-truy-xuất-lai-chống-ảo-giác-đa-lượt)  
   2.5. [Triển khai, tích hợp và vận hành](#25-triển-khai-tích-hợp-và-vận-hành)  
   2.6. [Phương pháp đánh giá và thực nghiệm gợi ý](#26-phương-pháp-đánh-giá-và-thực-nghiệm-gợi-ý)  
   2.7. [Rủi ro, quyền riêng tư và quản trị AI trong e-commerce](#27-rủi-ro-quyền-riêng-tư-và-quản-trị-ai-trong-e-commerce)  
3. [Kết luận và hướng mở rộng](#kết-luận-và-hướng-mở-rộng)  
4. [Tài liệu tham khảo gợi ý](#tài-liệu-tham-khảo-gợi-ý)

---

# Phần I — Khảo sát AI trong e-commerce

## 1.1. Bối cảnh và động lực

Thương mại điện tử là đấu trường của **dữ liệu khối lượng lớn**, **độ trễ chặt** và **trải nghiệm cá nhân hóa**. Người dùng tương tác liên tục qua nhiều kênh (web, ứng dụng di động, thông báo đẩy); mỗi sự kiện (xem sản phẩm, lọc danh mục, thêm vào giỏ, thanh toán, đánh giá) đều là tín hiệu để hệ thống học và điều chỉnh. Trí tuệ nhân tạo không chỉ là “một mô hình dự đoán” mà là **lớp các dịch vụ** gắn với từng điểm chạm: gợi ý đúng lúc, trả lời câu hỏi đúng ngữ cảnh, tìm kiếm bằng ảnh hoặc giọng nói, hỗ trợ vận hành (định tuyến kho, dự báo nhu cầu).

Động lực kinh doanh thường được đo bằng **chuyển đổi (conversion)**, **giá trị đơn hàng**, **tỷ lệ giữ chân** và **chi phí phục vụ** (CS). AI giúp tối ưu từng chỉ số: khuyến nghị tăng khả năng khám phá catalog; RAG giảm tải cho đội hỗ trợ bằng câu trả lời nhất quán với chính sách; tìm kiếm vector giúp người dùng diễn đạt nhu cầu mơ hồ (“sách tương tự cuốn X”) mà không cần từ khóa khớp chính xác.

Một điểm quan trọng: **dữ liệu e-commerce thay đổi nhanh** (giá, khuyến mãi, tồn kho). Do đó, các giải pháp chỉ dựa trên huấn luyện tĩnh một lần (ví dụ fine-tune LLM trên snapshot dữ liệu) thường thua các kiến trúc **tách retrieval (luôn cập nhật) khỏi generation (mô hình ngôn ngữ)**, như RAG. Đây là một trong những lý do khiến RAG trở thành mẫu hình phổ biến cho chatbot doanh nghiệp.

### Bản đồ ứng dụng AI trong e-commerce (khảo sát theo lớp nghiệp vụ)

Để thuận tiện đối chiếu với các chương sau, có thể hình dung AI trong e-commerce như một **ma trận**: hàng là giai đoạn hành trình khách hàng (tiếp cận → cân nhắc → mua → sau mua), cột là loại kỹ thuật (học có giám sát, học không giám sát, tối ưu hoá, sinh ngôn ngữ). Dưới đây là các nhóm ứng dụng hay gặp, không nhằm liệt kê đủ mọi startup hay sản phẩm, mà để **định vị** bài toán “phân tích hành vi & tư vấn” trong bức tranh lớn hơn.

1. **Tiếp thị và cá nhân hóa trải nghiệm:** gợi ý sản phẩm, cá nhân hóa trang chủ, thông báo đẩy theo ngữ cảnh (thời gian trong ngày, vị trí địa lý thô), email có nội dung sinh từ template + dữ liệu người dùng. Các mô hình thường kết hợp **hành vi lịch sử** với **đặc trưng sản phẩm** và **ràng buộc kinh doanh** (khuyến mãi đang chạy).

2. **Tìm kiếm và khám phá catalog:** ranking học được trên truy vấn–tài liệu, spell correction, synonym expansion, auto-complete ngữ nghĩa, và các đường **vector search** song song với keyword search (hybrid retrieval). Đây là nơi **embedding** trở thành “ngôn ngữ chung” giữa người dùng và hàng triệu SKU.

3. **Giá, khuyến mãi và quản trị nhu cầu:** định giá động, phân bổ coupon, dự báo nhu cầu theo SKU/region — thường đi kèp **tối ưu hóa ràng buộc** và **học tăng cường** khi không gian hành động rõ ràng. Mục tiêu không chỉ là lợi nhuận tức thời mà còn **tồn kho**, **thời gian giao**, và **trải nghiệm** (ví dụ tránh giảm giá quá sâu gây mất niềm tin).

4. **Rủi ro, gian lận và an ninh giao dịch:** phát hiện giao dịch bất thường, bot scraping, tài khoản bị chiếm đoạt, chargeback. Các mô hình thường là **classification** trên luồng sự kiện với đặc trưng tần suất và đồ thị; độ trễ yêu cầu có thể rất thấp (milliseconds) nên inference phải nhẹ.

5. **Hậu mãi và dịch vụ khách hàng:** phân loại ticket, gợi ý câu trả lời cho nhân viên (copilot), chatbot đa lượt với **RAG** neo vào chính sách nội bộ. Đây là nhóm **trùng khớp trực tiếp** với phần II của báo cáo: vừa cần độ chính xác nội dung, vừa cần **ngữ cảnh hành vi** để tư vấn phù hợp.

6. **Vận hành và chuỗi cung ứng:** dự báo SLA giao hàng, tối ưu lộ trình, phân bổ kho — thường là **tối ưu hóa tổ hợp** và mô hình dự báo chuỗi thời gian; AI đóng vai trò giảm chi phí vận hành hơn là “tăng doanh số trực tiếp” trên giao diện người dùng.

Khi đọc các báo cáo kỹ thuật công khai của sàn thương mại, hãy chú ý **đơn vị đo** (latency p95, throughput QPS, độ chính xác theo từng tầng). Một con số AUC cao ở tầng ranking không tự động đảm bảo trải nghiệm tốt nếu tầng recall quá hẹp hoặc re-ranking phá vỡ đa dạng.

## 1.2. Hệ thống khuyến nghị: từ lọc cơ bản đến pipeline đa tầng

### 1.2.1. Collaborative Filtering và Content-Based Filtering

**Lọc cộng tác (Collaborative Filtering, CF)** khai thác ma trận tương tác người–vật phẩm (user–item). Ma trận thường **thưa**: mỗi người chỉ tương tác một phần nhỏ catalog. Các phương pháp cổ điển gồm phân rã ma trận (matrix factorization), k-NN trên người dùng hoặc vật phẩm tương tự, và các biến thể tuyến tính. Điểm mạnh: khám phá được sở thích “tiềm ẩn” từ hành vi đám đông. Điểm yếu: **cold start** (user/item mới), và khó đưa metadata phong phú (mô tả, hình ảnh) vào một cách đồng nhất.

**Lọc dựa nội dung (Content-Based Filtering, CBF)** biểu diễn người dùng và sản phẩm trong **cùng không gian embedding** (vector đặc trưng). Độ phù hợp thường đo bằng tích vô hướng, cosine similarity hoặc học metric. CBF xử lý tốt trường hợp có mô tả văn bản/đặc trưng sản phẩm rõ ràng; song nếu chỉ dựa nội dung, hệ thống dễ bị **thiên lệch** (over-specialization): chỉ gợi ý các mục quá giống lịch sử, thiếu tính “bất ngờ có kiểm soát”.

Trong thực tế, các hệ thống lớn **pha trộn (blending)** nhiều tín hiệu: CF + CBF + quy tắc nghiệp vụ (ưu tiên hàng tồn, margin…).

### 1.2.2. Pipeline Recall → Ranking → Re-ranking

Ở quy mô công nghiệp, một mô hình đơn lẻ không đủ. Kiến trúc điển hình gồm ba giai đoạn:

1. **Recall (lọc thô):** từ hàng triệu SKU, trích nhanh một tập ứng viên nhỏ (vài trăm đến vài nghìn). Kỹ thuật hay gặp: **two-tower** (một tháp cho user, một tháp cho item, tối ưu tương đồng trong không gian embedding), kết hợp **ANN** (Approximate Nearest Neighbor) trên FAISS, ScaNN, HNSW… để đạt độ trễ cho phép.

2. **Ranking (xếp hạng):** đánh giá chi tiết từng cặp (user, candidate item) với đặc trưng phong phú: lịch sử duyệt theo chuỗi thời gian, ngữ cảnh phiên làm việc, thuộc tính sản phẩm. Các kiến trúc như **Deep Interest Network (DIN)** cho phép **attention** lên hành vi quá khứ để nhấn mạnh mức độ liên quan của từng sự kiện đối với candidate hiện tại. Mục tiêu có thể đa nhiệm: dự báo **CTR** (click), **CVR** (conversion), hoặc các proxy kinh doanh.

3. **Re-ranking:** tinh chỉnh thứ tự cuối theo ràng buộc và mục tiêu dài hạn: đa dạng hóa (không chỉ toàn một thể loại), công bằng giữa người bán, hoặc tối ưu **giá / khuyến mãi** trong biên an toàn. Một hướng là dùng **học tăng cường (RL)** với không gian hành động rời rạc (tăng/giảm/giữ mức ưu đãi, đẩy vị trí hiển thị…). Biến thể **Dueling DQN** tách ước lượng “giá trị trạng thái” và “lợi thế hành động”, giảm overestimation so với DQN cổ điển trong nhiều bài toán.

Xu hướng nghiên cứu mới — **Agentic Recommender Systems** — mô tả các module khuyến nghị như các agent có mục tiêu cục bộ, có thể kết hợp LLM để giảm phụ thuộc feature engineering thủ công. Tuy nhiên, trong production, pipeline ba giai đoạn vẫn là xương sống dễ lý giải và vận hành.

## 1.3. Tìm kiếm, đa phương thức và cơ sở dữ liệu vector

### 1.3.1. Giới hạn của full-text và vai trò embedding

Tìm kiếm full-text (inverted index, BM25, Elasticsearch…) mạnh khi người dùng nhập đúng từ khóa. Khi truy vấn mang tính **ngữ nghĩa** (“quà tặng cho người thích lịch sử Việt Nam”), cần **semantic search**: câu truy vấn và tài liệu được đưa qua mô hình embedding (Transformer, sentence-BERT…) thành vector, rồi so khớp theo cosine.

**Tìm kiếm đa phương thức** mở rộng: ảnh chụp sản phẩm → CNN/ViT trích vector; giọng nói → ASR → text → embedding. Pipeline thống nhất: **vector hóa** mọi loại dữ liệu về cùng một không gian (hoặc các không gian liên kết), sau đó **vector search**.

### 1.3.2. Quy mô và ANN

Với hàng chục triệu vector, duyệt k-NN chính xác là không khả thi trong SLA vài chục millisecond. Các cấu trúc **HNSW** (đồ thị phân tầng, tìm láng giềng xấp xỉ), IVF, PQ… cho phép đánh đổi độ chính xác nhỏ lấy tốc độ. **Milvus, Qdrant, Pinecone, Weaviate**… là các tên thường gặp; một số đội ngũ tự xây engine trên nền mã nguồn mở và tối ưu phần cứng (GPU, batching).

Case study công khai (ví dụ Shopee với Milvus) nhấn mạnh: **độ trễ thấp + cập nhật gia tăng** là yếu tố sống còn cho visual search và catalog lớn.

## 1.4. RAG và chatbot: từ quy tắc cứng đến sinh có neo

Chatbot rule-based (cây quyết định) dễ kiểm soát nhưng **vỡ** khi người dùng diễn đạt tự nhiên. LLM thuần sinh ra ngôn ngữ mượt nhưng **ảo giác** (hallucination) và **lỗi thời** nếu không có nguồn dữ liệu đúng.

**RAG (Retrieval-Augmented Generation)** tách bài toán thành:

- **Ingestion & chunking:** tài liệu chính sách, mô tả dịch vụ, FAQ được chia **chunk** có kích thước và chồng lấn (overlap) hợp lý để không mất ngữ cảnh ở biên.

- **Embedding & indexing:** mỗi chunk → vector, lưu trong vector store kèm **metadata** (nguồn, thời gian, danh mục).

- **Retrieval:** câu hỏi người dùng → vector truy vấn → top-k chunk gần nhất (có thể kết hợp lọc metadata).

- **Generation:** prompt ép mô hình **chỉ dựa vào ngữ cảnh đã trích** (grounding), trích dẫn nguồn (citation), và từ chối trả lời khi không đủ bằng chứng.

So với fine-tune LLM trên toàn bộ catalog, RAG **linh hoạt hơn** khi dữ liệu thay đổi: cập nhật index là đủ, không cần huấn luyện lại mô hình ngôn ngữ.

## 1.5. Định giá động, tối ưu suy luận và MLOps

### 1.5.1. Định giá động và RL

Định giá có thể xem như **quá trình ra quyết định Markov (MDP)**: trạng thái gồm giá đối thủ, tồn kho, nhu cầu; hành động là điều chỉnh giá hoặc coupon; phần thưởng là lợi nhuận hoặc doanh thu có ràng buộc. **DQN / Dueling DQN** là ví dụ thuật toán khi không gian trạng thái lớn và cần xấp xỉ hàm giá trị bằng mạng nơ-ron.

### 1.5.2. Quantization và inference

Để đáp ứng SLO độ trễ (ví dụ p95 dưới 100 ms cho một số đường), người ta **lượng tử hóa** (INT8/FP16), dùng ONNX Runtime, TensorRT, batching, và tách đường **đọc feature** (feature store) khỏi **suy luận**.

### 1.5.3. MLOps và streaming

**Feature store** giảm lệch train/serve: cùng một định nghĩa feature cho offline training và online serving. **Flink / Kafka** phục vụ luồng sự kiện; warehouse HTAP hỗ trợ truy vấn phân tích gần thời gian thực. Các case Lazada, Tiki, Shopee (theo bài báo kỹ thuật và blog) minh họa: **microservices + Kubernetes + pipeline dữ liệu** là nền để AI không chỉ “chạy demo” mà **chạy bền**.

## 1.6. Cold start, đa dạng, công bằng và giải thích được

**Cold start** là tình huống hệ thống thiếu lịch sử đủ dài: người dùng mới, sản phẩm mới, hoặc danh mục vừa mở. Chiến lược thường gặp: (i) **fallback** theo mục phổ biến / trending có kiểm soát; (ii) dùng **metadata** (thể loại, thuộc tính, văn bản mô tả) để CBF hoạt động sớm; (iii) **transfer** embedding từ sản phẩm tương tự; (iv) thu thập **explicit preference** trong onboarding (bước chọn sở thích ban đầu). Trong khuyến nghị đa tầng, tầng recall có thể mở rộng ứng viên khi tín hiệu cá nhân còn mỏng, còn tầng ranking học các đặc trưng “an toàn” hơn (ví dụ mức độ phổ biến có trọng số giảm dần theo thời gian tương tác).

**Đa dạng (diversity)** và **công bằng (fairness)** không chỉ là mục tiêu học thuật: chúng ảnh hưởng trực tiếp đến niềm tin người dùng và hệ sinh thái người bán. Một danh sách khuyến nghị chỉ toàn một nhãn hoặc một shop lớn sẽ làm giảm khả năng khám phá và gây “filter bubble”. Kỹ thuật re-ranking có thể áp **ràng buộc đa dạng** (tối đa N mục cùng thể loại), **điều tiết exposure** giữa người bán, hoặc penalty cho các pattern lặp lại. Tuy nhiên, cần cân bằng với **doanh thu ngắn hạn**: đôi khi độ đo kinh doanh (CTR) tăng khi danh sách đồng nhất — đây là lý do cần **đánh giá đa mục tiêu** và thử nghiệm A/B.

**Giải thích được (explainability)** trong e-commerce thường được hiểu theo nghĩa “thân thiện người dùng”: vì sao tôi thấy mục này (“vì bạn đã xem…”, “vì sản phẩm tương tự…”). Ở tầng kỹ thuật, attention trong DIN hoặc trọng số feature trong mô hình tuyến tính có thể cung cấp tín hiệu giải thích nội bộ; song cần tránh lộ thông tin nhạy cảm hoặc tạo cảm giác “theo dõi quá mức”. Với RAG, **trích dẫn nguồn** chính là dạng giải thích tự nhiên: người dùng biết câu trả lời bám vào đoạn chính sách nào.

## 1.7. Computer Vision, NLP sản phẩm và kiểm duyệt nội dung

**Thị giác máy tính** trong e-commerce vượt qua visual search: phát hiện **ảnh trùng / sao chép** trong catalog, nhận dạng **logo / nhãn hiệu** để gắn người bán đúng, kiểm tra **chất lượng ảnh** (mờ, viền trắng quá lớn) để chuẩn hóa trải nghiệm. Các mạng CNN/ViT trích vector đặc trưng; pipeline suy luận thường tối ưu bằng ONNX/TensorRT khi lưu lượng lớn.

**NLP cho sản phẩm** gồm: phân loại danh mục tự động, trích **thuộc tính** từ mô tả tự do, phát hiện ngôn từ không phù hợp, và **gắn tag** phục vụ tìm kiếm. Khi kết hợp embedding văn bản với embedding hình ảnh, có thể xây **đại diện đa phương thức** cho SKU — hữu ích cho đề xuất “cùng phong cách”.

**Kiểm duyệt và an toàn**: AI sinh nội dung (mô tả, trả lời chat) cần lớp **policy** — lọc PII, chống prompt injection, và tuân thủ pháp lý địa phương (quảng cáo, sản phẩm hạn chế). Đây là phần không thể tách khỏi “ứng dụng AI” trong bối cảnh thương mại.

## 1.8. Case study minh họa: Tiki, Shopee và xu hướng cloud-native

Các nền tảng lớn tại Việt Nam và khu vực thường công bố **mảnh ghép** kiến trúc qua blog kỹ thuật và hội thảo, không phải toàn bộ mã nguồn. Điều quan trọng là nhận ra **mẫu hình lặp lại**:

- **Tiki** (theo các bài trình bày công khai về hạ tầng): backend từng gắn với PHP hiệu năng cao, Elasticsearch cho tìm kiếm, MongoDB/Redis cho lớp dữ liệu phù hợp, và lộ trình **lên cloud** (ví dụ Google Kubernetes Engine) để co giãn theo sự kiện khuyến mãi. Góc AI có ví dụ dùng TensorFlow cho bài toàn **làm sạch catalog** (trùng lặp).

- **Shopee** (theo blog kỹ thuật): frontend hiện đại (React/Redux), backend phụ thuộc **Kafka + Spark** cho phân tích gần thời gian thực, Docker/Kubernetes cho vận hành, và **ClickHouse** phục vụ quan sát phân tán. Các module AI (routing kho, tối ưu vận hành) gắn với API lõi; song song, **vector search** được đầu tư mạnh (ví dụ xây engine trên Milvus) để phục vụ tìm kiếm đa phương tiện quy mô lớn.

- **Xu hướng chung:** tách **gateway**, **dịch vụ nghiệp vụ**, **dịch vụ dữ liệu**; chuẩn hóa CI/CD; đặt SLO theo **p95/p99** độ trễ; và coi **quan sát (logging, tracing, metrics)** là phần bắt buộc, không phụ trợ.

Các case này không nhằm “sao chép stack”, mà chỉ ra: **AI trong e-commerce = AI + dữ liệu + vận hành**. Sinh viên triển khai đồ án microservice ở quy mô nhỏ vẫn có thể mô phỏng tinh thần đó bằng container, cổng API duy nhất, và tách database theo service.

---

# Phần II — Ứng dụng: Phân tích hành vi & tư vấn dịch vụ

Phần này mô tả cách các khái niệm ở Phần I được **gói** thành một ứng dụng thống nhất trong bối cảnh một **hệ thương mại điện tử dạng microservice** (ví dụ hệ bookstore): thu thập hành vi, khuyến nghị sách, xây **kho tri thức** về dịch vụ, **chat tư vấn** dựa trên RAG, và **tích hợp** qua cổng vào duy nhất để người dùng không phải đối mặt với sự phức tạp phân tán.

## 2.1. Vị trí bài toán trong hệ e-commerce

### 2.1.1. Luồng nghiệp vụ tổng quan

Khách hàng đăng nhập, duyệt catalog, thêm giỏ, đặt hàng, thanh toán, nhận hàng, đánh giá. Mỗi bước sinh **sự kiện hành vi** có trọng số khác nhau: xem nhẹ hơn mua; thêm giỏ gợi ý ý định. Dịch vụ phân tích hành vi **ghi nhận** các sự kiện này (theo chuẩn REST nội bộ), tích lũy thành tín hiệu cho tầng khuyến nghị.

Song song, kênh **tư vấn** trả lời câu hỏi mang tính ngôn ngữ tự nhiên: “Gói vận chuyển nhanh áp dụng khi nào?”, “Sách X có phù hợp cho người mới không?”. Câu hỏi này không nên xử lý chỉ bằng if–else; cần **kho tri thức** đã chuẩn hóa và **RAG** để câu trả lời bám sát văn bản nội bộ.

### 2.1.2. Phân tách trách nhiệm (microservice)

Trong kiến trúc mẫu:

- **Cổng API (gateway)** là điểm vào duy nhất cho web: xác thực phiên, dựng trang, **proxy** các lời gọi tới dịch vụ nền (sách, giỏ, đơn, đánh giá…), và **proxy** luôn kênh AI chat để tránh vấn đề CORS và che giấu địa chỉ nội bộ.

- **Dịch vụ khuyến nghị / AI** tập trung logic: ghi nhận hành vi, sinh danh sách sách gợi ý, phục vụ endpoint chat. Dịch vụ này có thể **gọi ngược** các dịch vụ catalog/order để lấy ngữ cảnh (đơn đã mua, danh sách sách) khi cần làm giàu hồ sơ người dùng.

Như vậy, “ứng dụng phân tích hành vi để tư vấn dịch vụ” không phải một monolith: nó là **lớp trí tuệ** cắm vào hệ hiện có.

### 2.1.3. Hai lớp khuyến nghị thực tế: học ma trận và học sâu

Trong triển khai có thể đồng thời tồn tại:

- **Mô hình ma trận thưa (implicit feedback)** — ví dụ ALS — để gợi ý nhanh, ổn định khi dữ liệu tương tác đã đủ dày.

- **Pipeline học sâu** mô phỏng recall–ranking–re-ranking như một **đường ống nghiên cứu / nâng cấp**, có thể blend điểm số với tầng ma trận hoặc dùng embedding người dùng để làm giàu truy vấn RAG.

Điều này phản ánh thực tế công nghiệp: **không** luôn thay thế toàn bộ hệ thống cũ; mà **chồng** các tín hiệu mới khi đã kiểm chứng.

## 2.2. Mô hình học sâu cho hành vi (pipeline ba giai đoạn)

### 2.2.1. Ý tưởng tổng thể

Mô hình hành vi khách hàng được thiết kế theo tinh thần **CustomerBehaviorPipeline**: một pipeline học sâu gồm ba khối tương ứng ba giai đoạn khuyến nghị công nghiệp — **Recall**, **Ranking**, **Re-ranking**.

- **Giai đoạn Recall (hai tháp):**  
  Một nhánh mã hóa **người dùng** (lịch sử tương tác, đặc trưng ngữ cảnh), một nhánh mã hóa **đối tượng được khuyến nghị** (ở đây có thể là “dịch vụ” hoặc sản phẩm sách tùy cách ánh xạ dữ liệu). Hai vector được so khớp để mô phỏng tìm ứng viên nhanh. Hàm mất mát kiểu **InfoNCE** (contrastive) khuyến khích các cặp tương tác thực gần nhau và đẩy xa các cặp âm.

- **Giai đoạn Ranking (DIN):**  
  Khi đã có ứng viên, mô hình nhìn **chuỗi hành vi** (duyệt, click, thêm giỏ…) với cơ chế **attention** để nhấn mạnh phần lịch sử liên quan nhất tới ứng viên hiện tại. Đầu ra có thể gắn với **đa nhiệm**: xác suất click, chuyển đổi, hoặc các đầu phụ phục vụ phân loại (ví dụ thể loại).

- **Giai đoạn Re-ranking (Dueling DQN):**  
  Mô hình coi **trạng thái** là tổ hợp embedding người dùng và một vài chiều ngữ cảnh (ví dụ bối cảnh giá hoặc session). **Hành động** là một tập rời rạc hữu hạn (điều chỉnh chiến lược hiển thị/ưu đãi trong mô phỏng). **Dueling** tách dòng đánh giá giá trị trạng thái và lợi thế từng hành động — phù hợp tinh thần các bài toán tối ưu quyết định trong khuyến nghị và định giá.

### 2.2.2. Huấn luyện theo từng giai đoạn

Pipeline được huấn luyện **lần lượt** (multi-stage): trước hết cố định/thúc đẩy tầng recall, sau đó ranking, cuối cùng là DQN với **mạng đích (target network)** cập nhật chậm để ổn định học Q. Cách này giống thực hành “pretrain từng phần” giúp giảm xung đột gradient và dễ debug.

Dữ liệu huấn luyện có thể là **tổng hợp có kiểm soát** (dataset giả lập quy mô lớn) trong môi trường học tập; khi lên production, cần thay bằng log thật và pipeline đánh nhãn (implicit label từ hành vi).

### 2.2.3. Checkpoint và suy luận

Sau huấn luyện, trọng số được lưu thành **checkpoint** duy nhất cho toàn pipeline. Lúc phục vụ, một thành phần singleton (khởi tạo một lần khi process sống) có thể **nạp** checkpoint, đặt trên CPU hoặc GPU tùy môi trường. Nếu file checkpoint chưa tồn tại (chưa train), hệ thống có thể **không** ép buộc DL mà chỉ dựa các tầng nhẹ hơn — điều này giúp triển khai từng bước.

### 2.2.4. Liên kết với tư vấn: embedding người dùng và điểm dịch vụ

Embedding người dùng từ tháp người dùng có thể đưa sang **RAG** như một phần **làm giàu truy vấn** (query enrichment): hệ thống không chỉ hỏi bằng câu chữ mà còn “gợi ý ngầm” sở thích từ hành vi. Tương tự, điểm từ tầng ranking/re-ranking có thể đóng vai trò **re-rank** các chunk dịch vụ sau bước truy xuất vector — tức **hybrid + behavioral re-ranking**, đúng tinh thần “multi-stage” ngoài đời.

## 2.3. Knowledge base phục vụ tư vấn

### 2.3.1. Nội dung và mục tiêu

Knowledge base (KB) không chỉ là “một file văn bản dài”. Nó là **tập tài liệu có cấu trúc ngầm**: mỗi mục dịch vụ (hoặc sách/dịch vụ gia tăng) có **mã định danh**, **tên**, **danh mục**, **mô tả**, **khoảng giá** (nếu có), **thẻ (tags)**. Văn bản mô tả được **chia chunk** với overlap để tránh cắt đứt ý ở giữa đoạn.

### 2.3.2. Chỉ mục kép: văn bản và tín hiệu hành vi

Để phục vụ **truy xuất lai (hybrid retrieval)**, KB được biểu diễn thành ít nhất hai góc nhìn bổ sung:

- **Chỉ mục ngữ nghĩa văn bản:** embedding câu/đoạn bằng mô hình sentence-transformer phổ biến (ví dụ các biến thể MiniLM) — phục vụ câu hỏi diễn đạt tự nhiên.

- **Chỉ mục gắn với đường học sâu:** vector “dịch vụ” tương thích với không gian embedding dùng trong tầng recall — cho phép đồng nhất **truy vấn ngôn ngữ** với **sở thích hành vi** khi có embedding người dùng.

Metadata (JSON hoặc tương đương) lưu song song để hiển thị nguồn, lọc theo danh mục, và **ưu tiên độ mới** (freshness) nếu có trường thời gian.

### 2.3.3. Lưu trữ vector và HNSW

Thực tế triển khai thường dùng **FAISS** với chỉ mục **HNSW** cho tra cứu láng giềng gần xấp xỉ nhanh. Hai chỉ mục (text và behavioral) cùng metadata cho phép lớp retriever **hợp nhất điểm** trong một pipeline tìm kiếm thống nhất.

### 2.3.4. Vòng đời KB

- **Khởi tạo:** ingest từ nguồn nội bộ (file, export catalog dịch vụ).  
- **Cập nhật:** khi mô tả/ giá / chính sách thay đổi, **build lại** chunk và vector (trong hệ nhỏ có thể offline; trong hệ lớn dùng job định kỳ hoặc luồng incremental).  
- **Kiểm thử:** truy vấn mẫu để đảm bảo top-k không trống và không trùng lặp vô nghĩa.

## 2.4. RAG: truy xuất lai, chống ảo giác, đa lượt

### 2.4.1. Luồng xử lý một lượt hội thoại

Khi người dùng gửi câu hỏi, pipeline RAG thực hiện các bước khái niệm sau:

1. **Làm giàu truy vấn:** ghép gợi ý từ **hồ sơ** (độ tuổi, sở thích, khu vực — nếu có) vào phía trước câu hỏi để embedding phản ánh ngữ cảnh cá nhân.

2. **Truy xuất:** embedding truy vấn (có thể kết hợp embedding hành vi) → tìm top-k chunk trong vector store; áp ngưỡng điểm tối thiểu để loại nhiễu.

3. **Tái sắp xếp (tuỳ chọn):** nếu có **điểm dịch vụ** từ mô hình hành vi (ánh xạ theo mã dịch vụ), trộn điểm truy xuất văn bản và điểm hành vi (ví dụ tỷ lệ cố định) rồi sắp xếp lại — tương tự bước re-ranking trong khuyến nghị.

4. **Ước lượng độ tin cậy:** dựa trên độ tương đồng và mức khớp chủ đề giữa câu hỏi và chunk.

5. **Dựng prompt có neo:** hệ thống prompt **bắt buộc** mô hình ngôn ngữ trả lời dựa trên khối ngữ cảnh đã trích; nếu không có ngữ cảnh đủ mạnh, trả lời thận trọng hoặc từ chối.

6. **Sinh câu trả lời:** gọi backend LLM (API cloud hoặc máy cục bộ tùy cấu hình) với **giới hạn kiến thức** từ KB.

7. **Trích dẫn:** liệt kê tên dịch vụ / nguồn chunk được dùng; đối chiếu mặt chữ trong câu trả lời để hỗ trợ minh bạch.

8. **Bộ nhớ hội thoại ngắn:** lưu vài lượt trước để đa lượt liên tục (“còn gói rẻ hơn không?”) mà không mất ngữ cảnh.

### 2.4.2. Anti-hallucination theo thiết kế

Các cơ chế **grounding** (chỉ dùng context đã cấp), **citation**, **ngưỡng confidence**, và **fallback** khi không retrieve được chunk phù hợp là các lớp an toàn nội dung. Đây là điểm khác biệt so với chatbot chỉ “sinh tự do”.

### 2.4.3. Giao diện người dùng và proxy

Phía trình duyệt có thể nhúng **widget chat** gọi đến endpoint REST trên cổng chính; cổng chuyển tiếp sang dịch vụ AI để tránh lỗi cross-origin và để tập trung **retry / timeout** (AI thường cần thời gian dài hơn CRUD thông thường khi nạp mô hình lần đầu).

## 2.5. Triển khai, tích hợp và vận hành

### 2.5.1. Container hóa và mạng nội bộ

Toàn bộ hệ có thể đóng gói **Docker Compose**: mỗi bounded context một dịch vụ, một cơ sở dữ liệu riêng (theo nguyên tắc database-per-service). Dịch vụ AI lắng nghe trên cổng riêng; cổng gọi qua mạng ảo nội bộ theo tên dịch vụ.

### 2.5.2. Tích hợp qua API Gateway

**Gợi ý sách:** trang khách hàng yêu cầu danh sách id sách gợi ý; gateway có thể **hydrate** thêm chi tiết sách bằng các lời gọi tuần tự tới dịch vụ sách. Đồng thời, khi người dùng thêm vào giỏ từ trang gợi ý, gateway có thể **bắn sự kiện hành vi** về dịch vụ khuyến nghị để khép kín vòng lặp học.

**Chat tư vấn:** luồng POST JSON qua proxy; lỗi kết nối tạm thời được **thử lại** vài lần vì dịch vụ AI có thể khởi động chậm hơn các dịch vụ CRUD.

### 2.5.3. Huấn luyện định kỳ

Có thể cấu hình **cron** trong dịch vụ AI để chạy lệnh huấn luyện vào khung giờ thấp tải (ví dụ đêm), ghi đè checkpoint. Đây là bước nhỏ hướng tới **closed-loop**: hành vi mới → mô hình cập nhật định kỳ → gợi ý/tư vấn phản ánh gần với hiện tại hơn. (Trong thực tế production cần thêm theo dõi drift, rollback, và kiểm định A/B.)

### 2.5.4. Biến môi trường và khóa API

Khóa truy cập LLM và cấu hình endpoint nên đặt trong **biến môi trường**, tách khỏi mã; file môi trường có thể nằm ở **thư mục gốc monorepo** để mọi dịch vụ đọc thống nhất. Điều này giảm rủi ro lộ secret khi chia sẻ mã nguồn trong lớp học.

### 2.5.5. Giới hạn và cách nâng cấp

- **Quy mô dữ liệu:** ALS và vector search nhỏ đủ cho đồ án; catalog lớn cần sharding index và batch embedding.  
- **Độ trễ:** RAG + LLM chậm hơn rule-based; cần cache câu hỏi thường gặp, giảm top-k, hoặc mô hình nhỏ hơn.  
- **An toàn:** lọc PII trong log; policy nội dung cho LLM; giám sát prompt injection.  
- **Đánh giá:** offline (NDCG, AUC) và online (click-through, CSAT chat).

## 2.6. Phương pháp đánh giá và thực nghiệm gợi ý

### 2.6.1. Đánh giá khuyến nghị (offline)

Khi có lịch sử tương tác được chia **theo thời gian** (train trước, test sau), các chỉ số thường dùng gồm:

- **AUC** cho bài toán dự báo nhị phân (click / không click) trên cặp (user, item) được lấy mẫu có nhãn.

- **Recall@K** và **NDCG@K** để đo chất lượng danh sách top-K so với các mục người dùng thực sự tương tác trong tương lai gần.

- **Hit-rate@K** khi chỉ cần biết “có ít nhất một đúng trong K”.

Với pipeline nhiều tầng, nên báo cáo **theo giai đoạn**: recall có đủ ứng viên không; ranking có xếp đúng thứ tự không; re-ranking có cải thiện đa dạng / mục tiêu kinh doanh không. Nếu chỉ báo một con số tổng hợp, rất khó **debug** khi mô hình suy giảm.

### 2.6.2. Đánh giá RAG (offline + bán tự động)

RAG cần hai lớp đo:

- **Retrieval:** độ phủ (có chunk vàng trong top-k không?), **MRR**, **nDCG** trên tập câu hỏi–tài liệu chuẩn; và tỷ lệ “không retrieve được gì” (failure rate).

- **Generation:** độ trung thực với ngữ cảnh (faithfulness) — có thể dùng mô hình chấm điểm hoặc luật heuristics (cấm khái niệm không xuất hiện trong context); **từ chối trả lời đúng lúc** khi không đủ bằng chứng cũng là một độ đo chất lượng.

Trong môi trường học thuật, có thể xây **bộ câu hỏi mẫu** theo từng danh mục dịch vụ (vận chuyển, đổi trả, gói hội viên…) và kiểm định định kỳ sau mỗi lần cập nhật KB.

### 2.6.3. Thử nghiệm trực tuyến (A/B)

Tiêu chuẩn vàng vẫn là **A/B** trên lưu lượng thật: nhóm điều khiển vs nhóm có tính năng mới (ví dụ blend ALS + điểm DL, hoặc RAG có/không re-rank hành vi). Cần xác định trước **metric chính** (conversion, GMV, thời gian phiên) và **guardrail** (độ trễ p95, tỷ lệ lỗi 5xx). Với đồ án, có thể mô phỏng A/B nhỏ bằng canary release hoặc ghi log để so sánh trước/sau có kiểm soát.

## 2.7. Rủi ro, quyền riêng tư và quản trị AI trong e-commerce

### 2.7.1. Dữ liệu hành vi và minh bạch

Thu thập hành vi (view, add-to-cart, purchase) là nền tảng của cá nhân hóa, nhưng cần **thông báo** và **mục đích rõ ràng** theo các khung pháp lý hiện hành. Ẩn danh hóa định danh nội bộ, hạn chế lưu trữ dữ liệu nhạy cảm trong log suy luận, và **thu hồi / xóa** theo yêu cầu người dùng là các nguyên tắc tối thiểu.

### 2.7.2. Sai lệch và vòng lặp phản hồi

Hệ thống khuyến nghị có thể **củng cố** sở thích cũ: người dùng chỉ thấy một dải sản phẩm → chỉ tương tác trong dải đó → mô hình càng tin dải đó là “đúng”. Các biện pháp giảm hiệu ứng này gồm **khám phá có chủ đích** (epsilon-greedy trong gợi ý), đa dạng hóa ở re-ranking, và định kỳ **đánh giá nhóm** (ví dụ người dùng mới vs cũ).

### 2.7.3. An toàn LLM và RAG

Ngay cả khi có RAG, mô hình ngôn ngữ vẫn có thể **bị lừa** bằng câu hỏi mơ hồ hoặc chứa chỉ dẫn ẩn (prompt injection). Biện pháp: phân quyền rõ ràng giữa **người dùng cuối** và **nhân viên nội bộ**, lọc đầu vào, giới hạn độ dài lịch sử, và **không** để LLM thực thi hành động nhạy cảm (hoàn tiền, đổi địa chỉ) mà không qua API nghiệp vụ có xác thực.

### 2.7.4. Sẵn sàng vận hành (operational readiness)

Trong microservice, lỗi một dịch vụ AI không được làm **sập** toàn trang mua sắm. Thiết kế nên cho phép **degrade gracefully**: nếu chat AI không khả dụng, vẫn hiển thị FAQ tĩnh; nếu khuyến nghị nâng cao lỗi, fallback sang top rated hoặc trending. Retry có backoff (như đã mô tả ở proxy) giúp vượt qua giai đoạn khởi động nặng của mô hình.

## 2.8. Tích hợp vào web BookStore

### 2.8.1. Tích hợp chatbot tư vấn (kèm ảnh chụp giao diện)

Ở mức giao diện người dùng, chatbot được nhúng bằng widget JavaScript ở góc phải trang khách hàng. Khi người dùng bấm mở chat, widget tạo một phiên hội thoại ngắn hạn, gửi câu hỏi qua gateway và nhận câu trả lời từ dịch vụ AI theo cơ chế streaming hoặc trả về một lần tùy cấu hình.

Luồng xử lý tổng quát:

1. **User input:** người dùng nhập câu hỏi (ví dụ: "Mình cần sách nhập môn AI cho người mới").
2. **Gateway proxy:** frontend gửi `POST /api/ai/chat` về gateway; gateway thêm thông tin phiên và chuyển tiếp nội bộ sang dịch vụ AI.
3. **RAG pipeline:** dịch vụ AI thực hiện retrieval từ KB, re-rank theo tín hiệu hành vi (nếu có), rồi gọi LLM để sinh câu trả lời có neo.
4. **Response render:** widget hiển thị nội dung trả lời, kèm danh sách nguồn tham chiếu (tên tài liệu/chunk) nếu bật citation.
5. **Logging sự kiện:** hệ thống ghi log tối thiểu (thời gian phản hồi, loại câu hỏi, trạng thái thành công/thất bại) để theo dõi chất lượng.

Gợi ý chèn hình minh họa trong báo cáo:

- **Hình 2.4:** Ảnh chụp màn hình trang web khi chatbot ở trạng thái đóng (nút chat nổi).  
- **Hình 2.5:** Ảnh chụp cửa sổ hội thoại với một lượt hỏi–đáp thực tế, có thể che thông tin nhạy cảm nếu cần.

*Chú thích hình đề xuất:* "Widget chatbot tư vấn sách được tích hợp ở frontend và gọi qua API Gateway đến dịch vụ RAG."

### 2.8.2. Mô tả luồng recommend từ hành vi đến hiển thị

Luồng khuyến nghị trong website BookStore có thể mô tả theo chu trình khép kín:

1. **Thu thập hành vi:** frontend gửi các sự kiện `view`, `add_to_cart`, `purchase` về backend (qua gateway hoặc event endpoint riêng).
2. **Cập nhật hồ sơ người dùng:** dịch vụ AI/khuyến nghị tổng hợp tín hiệu thành vector người dùng hoặc đặc trưng phiên gần nhất.
3. **Recall ứng viên:** tầng recall lấy danh sách ứng viên ban đầu từ ANN/ALS (vài trăm đến vài nghìn item).
4. **Ranking & re-ranking:** các ứng viên được chấm điểm theo mô hình học sâu và điều chỉnh bởi ràng buộc đa dạng, độ mới, hoặc ưu tiên nghiệp vụ.
5. **Trả danh sách gợi ý:** endpoint recommend trả về danh sách `book_id` + điểm; gateway hydrate thêm metadata sách từ catalog service.
6. **Hiển thị trên UI:** trang chủ/trang chi tiết render block "Gợi ý cho bạn"; khi người dùng click vào gợi ý, vòng lặp dữ liệu được cập nhật trở lại.

Gợi ý chèn hình minh họa trong báo cáo:

- **Hình 2.6:** Ảnh chụp block "Sách gợi ý cho bạn" trên trang web (đánh dấu các item được recommend).  
- **Hình 2.7:** Ảnh chụp log/request-response mẫu của endpoint recommend (hoặc sequence diagram đơn giản Gateway -> Recommender -> Catalog -> Frontend).

*Chú thích hình đề xuất:* "Luồng khuyến nghị đóng vòng: hành vi người dùng -> mô hình đề xuất -> hiển thị -> hành vi mới."

Với cách trình bày này, mục 2.8 vừa có bằng chứng triển khai trực quan (screenshot), vừa thể hiện rõ luồng kỹ thuật end-to-end để liên kết với các phần lý thuyết ở Mục 2.2 và 2.4.

---

# Kết luận và hướng mở rộng

AI trong e-commerce là **hệ sinh thái** gồm dữ liệu, mô hình, infra và quy trình. Khảo sát Phần I cho thấy các mảng: khuyến nghị đa tầng, tìm kiếm vector, RAG cho dịch vụ khách hàng, RL cho quyết định giá/ưu đãi, và MLOps cho vận hành bền. Phần II đã ánh xạ các khái niệm đó vào bài toán **phân tích hành vi để tư vấn dịch vụ** trong một hệ microservice: pipeline học sâu ba giai đoạn làm xương sống cho tín hiệu hành vi; knowledge base hai chỉ mục phục vụ truy xuất lai; RAG neo câu trả lời vào tài liệu nội bộ; cổng API thống nhất luồng người dùng và proxy AI.

Hướng mở rộng hợp lý cho đồ án hoặc luận văn tiếp theo gồm: **offline evaluation** có kiểm soát cho từng tầng; **A/B testing** trên gợi ý; **feature store** thống nhất; **quan sát** (metrics, trace) cho đường AI; và **bảo mật** (ẩn danh hóa log hành vi, kiểm duyệt nội dung sinh).

---

# Tài liệu tham khảo gợi ý

1. Google Developers — *Content-based filtering basics* (Machine Learning — Recommendation), https://developers.google.com/machine-learning/recommendation/content-based/basics — truy cập tháng 4/2026.  
2. Zhou et al. — *Deep Interest Network for Click-Through Rate Prediction* (ACM KDD), bài báo gốc về DIN.  
3. Wang, Schaul et al. — *Dueling Network Architectures for Deep Reinforcement Learning* (ICML 2016).  
4. Lewis et al. — *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (NeurIPS 2020).  
5. Malkov, Yashunin — *Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs* (HNSW).  
6. Tài liệu kỹ thuật / blog công khai của các nền tảng e-commerce (Shopee, Lazada, Tiki) về data pipeline, search, và migration cloud — dùng làm minh họa triển khai thực tế (luôn đối chiếu ngày và phiên bản).

---

## Phụ lục A: Thuật ngữ (gọn, tra cứu nhanh)

| Thuật ngữ | Giải thích ngắn |
|-----------|-----------------|
| **ANN (Approximate Nearest Neighbor)** | Tìm láng giềng gần xấp xỉ trong không gian vector để giảm độ phức tạp so với k-NN đúng. |
| **ALS (Alternating Least Squares)** | Thuật toán phổ biến cho matrix factorization với ma trận thưa, dùng nhiều trong implicit feedback. |
| **Attention** | Cơ chế gán trọng số cho từng phần đầu vào (ví dụ từng sự kiện trong lịch sử) — lõi của nhiều mô hình ranking hiện đại. |
| **Checkpoint** | File lưu trọng số mô hình sau huấn luyện, dùng để nạp lại khi suy luận. |
| **Chunking** | Chia văn bản dài thành đoạn nhỏ để embedding và truy xuất hiệu quả trong RAG. |
| **Cold start** | Thiếu dữ liệu lịch sử cho user hoặc item mới. |
| **CTR / CVR** | Tỷ lệ click / tỷ lệ chuyển đổi (mua, đăng ký…) — thường là mục tiêu dự báo ở tầng ranking. |
| **DQN / Dueling DQN** | Học tăng cường sâu; Dueling tách giá trị trạng thái và lợi thế hành động. |
| **Embedding** | Vector đặc trưng biểu diễn đối tượng trong không gian số chiều cao. |
| **FAISS** | Thư viện Facebook AI cho tìm kiếm vector và chỉ mục ANN. |
| **Grounding** | Bắt buộc câu trả lời dựa trên bằng chứng đã cấp (ngữ cảnh trích từ KB). |
| **HNSW** | Thuật toán đồ thị phân tầng cho ANN, cân bằng tốc độ và độ chính xác. |
| **Hybrid retrieval** | Kết hợp nhiều nguồn điểm (ví dụ semantic + hành vi) khi tìm tài liệu. |
| **InfoNCE** | Hàm contrastive learning thường dùng để huấn luyện hai tháp (user/item). |
| **KB (Knowledge Base)** | Kho tài liệu có cấu trúc phục vụ tư vấn / RAG. |
| **LLM** | Mô hình ngôn ngữ lớn, dùng cho bước sinh câu trả lời trong RAG. |
| **MDP** | Quá trình ra quyết định Markov — khung toán học cho RL. |
| **MLOps** | Thực hành kỹ thuật đưa ML vào production: versioning, CI/CD, monitoring. |
| **NDCG@K** | Chuẩn hóa discounted cumulative gain — đo chất lượng thứ hạng top-K. |
| **RAG** | Retrieval-Augmented Generation: truy xuất trước, sinh sau. |
| **Two-tower** | Kiến trúc hai nhánh mã hóa user và item rồi so khớp embedding. |

---

## Phụ lục B: Gợi ý trình bày khi chuyển sang Word/PDF (~20 trang)

- **Font và cỡ chữ:** Times New Roman hoặc serif học thuật, 13–14 pt nội dung, 1.3–1.5 dòng.  
- **Lề:** 2,5 cm trái/phải, 2 cm trên/dưới.  
- **Mục lục tự động** theo Heading 1–3.  
- **Hình minh họa:** một sơ đồ luồng (Gateway → Dịch vụ AI → Vector DB + LLM) và một sơ đồ pipeline Recall–Ranking–Re-ranking — có thể vẽ lại từ ý trong Phần II mà không cần trích mã.  
- **Đánh số hình, bảng** (nếu thêm bảng so sánh CF vs CBF vs RAG).  
- **Trích dẫn** theo IEEE hoặc Harvard thống nhất với đề cương môn học.

*Tài liệu này được soạn ở định dạng Markdown để sao chép vào thư mục tài liệu dự án. Sau khi mở rộng các mục khảo sát (cold start, fairness, CV/NLP, case study) và các mục đánh giá / rủi ro / quản trị AI, tổng khối lượng chữ thường đạt khoảng **11000–14000 từ** tiếng Việt (tùy font và cách đếm), tương đương **khoảng 18–24 trang** A4 nếu in với Times New Roman 13 pt, giãn dòng 1.3–1.5, lề chuẩn báo cáo. Có thể thêm hình sơ đồ kiến trúc và bảng so sánh để đạt đúng 20 trang theo yêu cầu định dạng của giảng viên.*
