import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
from thefuzz import process, fuzz

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="Trợ Lý Giải Đề AI", page_icon="🎓")

st.title("🎓 Trợ Lý Giải Đề & Chống Đảo Đáp Án")

# --- SIDEBAR: Cấu hình ---
with st.sidebar:
    st.header("⚙️ Cấu hình")
    api_key = st.text_input("1. Nhập Gemini API Key", type="password")
    
    # [MỚI] Cho phép bạn tự điền tên mô hình (Ví dụ: gemini-2.5-flash)
    model_name = st.text_input("2. Tên Mô hình (Model Name)", value="gemini-1.5-flash")
    st.caption("Gợi ý: gemini-1.5-flash, gemini-2.0-flash-exp, hoặc tên model bạn thấy trong Console.")
    
    st.divider()
    
    st.info("3. Upload file Ngân hàng câu hỏi")
    uploaded_file = st.file_uploader("Chọn file Excel/CSV", type=["xlsx", "csv", "xls"])

    col_question = st.text_input("Tên cột Câu Hỏi", value="Question")
    col_answer = st.text_input("Tên cột Đáp Án", value="Answer")

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

def get_gemini_response(model, image, prompt):
    try:
        response = model.generate_content([prompt, image])
        return response.text.strip()
    except Exception as e:
        st.error(f"Lỗi Gemini: {e}")
        return None

# --- GIAO DIỆN CHÍNH ---
if not api_key:
    st.warning("⚠️ Vui lòng nhập API Key để bắt đầu.")
    st.stop()

# Cấu hình API với tên mô hình bạn nhập
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name) # <--- Sửa đổi quan trọng ở đây
except Exception as e:
    st.error(f"Cấu hình thất bại: {e}")
    st.stop()

if uploaded_file is None:
    st.warning("⚠️ Vui lòng tải lên file dữ liệu.")
    st.stop()

df = load_data(uploaded_file)

if df is not None:
    st.success(f"✅ Đã tải {len(df)} câu hỏi.")

    st.divider()
    img_file = st.file_uploader("📸 Tải ảnh đề thi lên đây", type=["jpg", "png", "jpeg"])

    if img_file:
        image = Image.open(img_file)
        st.image(image, caption="Ảnh đề thi", use_container_width=True)

        if st.button("🚀 GIẢI ĐỀ NGAY", type="primary"):
            with st.spinner("🤖 Đang xử lý..."):
                
                # BƯỚC 1: Đọc câu hỏi
                q_text = get_gemini_response(model, image, "Trích xuất câu hỏi chính. Chỉ lấy text, không lấy đáp án.")
                
                if q_text:
                    st.write(f"**🔍 Đọc được:** {q_text}")
                    
                    # BƯỚC 2: Tìm trong Excel
                    try:
                        choices = df[col_question].dropna().astype(str).tolist()
                        best_match, score = process.extractOne(q_text, choices, scorer=fuzz.token_sort_ratio)
                    except KeyError:
                        st.error(f"Sai tên cột '{col_question}'. Kiểm tra lại file Excel.")
                        st.stop()

                    if score > 60: 
                        row = df[df[col_question] == best_match].iloc[0]
                        correct_ans = row[col_answer]

                        st.success("✅ **ĐÃ TÌM THẤY!**")
                        st.info(f"📖 **Đáp án đúng:** {correct_ans}")

                        # BƯỚC 3: Chống đảo đề
                        check_prompt = f"""
                        Đáp án đúng là: "{correct_ans}".
                        Nhìn vào ảnh, nội dung đáp án này nằm ở vị trí A, B, C hay D?
                        Trả lời ngắn: "Chọn [X] vì [Lý do]".
                        """
                        advice = get_gemini_response(model, image, check_prompt)
                        st.markdown(f"### 💡 {advice}")
                    else:
                        st.error(f"❌ Không tìm thấy (Độ khớp: {score}%).")
