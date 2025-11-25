import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
from PIL import Image
from thefuzz import process, fuzz

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Trợ Lý Giải Đề AI", page_icon="🎓")

st.title("🎓 Trợ Lý Giải Đề & Chống Đảo Đáp Án")
st.write("Tải ảnh câu hỏi lên, AI sẽ tìm đáp án đúng trong Excel và chỉ cho bạn vị trí trên ảnh.")

# --- SIDEBAR: Cấu hình ---
with st.sidebar:
    st.header("⚙️ Cấu hình")
    api_key = st.text_input("Nhập Gemini API Key", type="password")
    
    st.info("Upload file Ngân hàng câu hỏi (Excel/CSV)")
    uploaded_file = st.file_uploader("Chọn file dữ liệu", type=["xlsx", "csv", "xls"])

    # Chọn cột dữ liệu
    col_question = st.text_input("Tên cột Câu Hỏi", value="Question")
    col_answer = st.text_input("Tên cột Đáp Án (Nội dung)", value="Answer")

# --- HÀM XỬ LÝ ---
def load_data(file):
    try:
        if file.name.endswith('.csv'):
            return pd.read_csv(file)
        else:
            return pd.read_excel(file)
    except Exception as e:
        st.error(f"Lỗi đọc file: {e}")
        return None

def get_gemini_response(client, image, prompt):
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                types.Content(
                    parts=[
                        types.Part.from_image(image),
                        types.Part.from_text(text=prompt)
                    ]
                )
            ]
        )
        return response.text.strip()
    except Exception as e:
        st.error(f"Lỗi Gemini: {e}")
        return None

# --- GIAO DIỆN CHÍNH ---
if not api_key:
    st.warning("⚠️ Vui lòng nhập API Key ở thanh bên trái để bắt đầu.")
    st.stop()

if uploaded_file is None:
    st.warning("⚠️ Vui lòng tải lên file Excel ngân hàng câu hỏi.")
    st.stop()

# Load dữ liệu
df = load_data(uploaded_file)

if df is not None:
    st.success(f"✅ Đã tải {len(df)} câu hỏi vào bộ nhớ.")

    # Upload ảnh câu hỏi
    st.divider()
    st.subheader("📸 Chụp/Tải ảnh câu hỏi")
    img_file = st.file_uploader("Upload ảnh đề thi", type=["jpg", "png", "jpeg"])

    if img_file:
        image = Image.open(img_file)
        st.image(image, caption="Ảnh đề thi", use_container_width=True)

        if st.button("🚀 GIẢI ĐỀ NGAY", type="primary"):
            with st.spinner("🤖 Đang đọc đề và tra cứu..."):
                client = genai.Client(api_key=api_key)

                # BƯỚC 1: Đọc câu hỏi
                q_text = get_gemini_response(client, image, "Trích xuất nội dung câu hỏi chính trong ảnh. Chỉ lấy text câu hỏi, không lấy đáp án.")
                
                if q_text:
                    st.write(f"**🔍 Đọc được:** {q_text}")
                    
                    # BƯỚC 2: Tìm trong Excel (Fuzzy Search)
                    # Lấy danh sách câu hỏi từ cột user nhập
                    try:
                        choices = df[col_question].dropna().astype(str).tolist()
                        best_match, score = process.extractOne(q_text, choices, scorer=fuzz.token_sort_ratio)
                    except KeyError:
                        st.error(f"Không tìm thấy cột '{col_question}' trong file Excel. Hãy kiểm tra lại tên cột ở Sidebar.")
                        st.stop()

                    if score > 60: # Độ tin cậy trên 60%
                        # Lấy dòng tương ứng
                        row = df[df[col_question] == best_match].iloc[0]
                        correct_answer_content = row[col_answer]

                        st.success("✅ **ĐÃ TÌM THẤY TRONG KHO!**")
                        st.info(f"📖 **Nội dung đáp án đúng:** {correct_answer_content}")

                        # BƯỚC 3: Soi lại ảnh để chống đảo đề
                        check_prompt = f"""
                        Đáp án đúng của câu này là: "{correct_answer_content}".
                        Hãy nhìn vào bức ảnh này, tìm xem nội dung đáp án đó đang nằm ở vị trí A, B, C hay D?
                        Hãy trả lời ngắn gọn: "Bạn nên chọn [X] vì [Lý do ngắn]".
                        """
                        
                        advice = get_gemini_response(client, image, check_prompt)
                        st.markdown(f"### 💡 {advice}")
                        
                    else:
                        st.error(f"❌ Không tìm thấy câu hỏi này trong ngân hàng dữ liệu (Độ khớp cao nhất: {score}%).")
                        st.write(f"Câu hỏi giống nhất tìm được: {best_match}")