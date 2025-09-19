import streamlit as st
import pandas as pd
import os
import io
import zipfile
import tempfile
from google import genai
from google.genai import types
import wave
from dotenv import load_dotenv
from datetime import datetime
import time

# Load environment variables
load_dotenv()

# Initialize Gemini client
@st.cache_resource
def init_client():
    # Try Streamlit secrets first, then environment variables
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except:
        api_key = os.environ.get("GEMINI_API_KEY")

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            client_args={"timeout": 60.0}  # 秒
        )
    )

# Wave file creation function
def create_wave_file(pcm_data, channels=1, rate=24000, sample_width=2):
    """Create a wave file in memory from PCM data"""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)
    buffer.seek(0)
    return buffer

# TTS generation function
def generate_tts(client, text, voice="Zephyr", instruction="", temperature=1.0, model="gemini-2.5-pro-preview-tts"):
    """Generate TTS for given text with specified parameters and instructions"""
    try:
        # Combine instruction and text if instruction is provided
        if instruction:
            contents = f"""Instructions: {instruction}

Please read the following lines according to the instructions above:
"{text}" """
        else:
            contents = text
        
        print(f"  🔄 Calling API with temperature={temperature}, voice={voice}")
        
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=temperature,
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice,
                        )
                    )
                ),
            )
        )
        
        if not response or not response.candidates:
            print(f"  ⚠️ Empty response from API")
            return None
            
        pcm_data = response.candidates[0].content.parts[0].inline_data.data
        print(f"  ✅ Generated audio ({len(pcm_data)} bytes)")
        return pcm_data
    except Exception as e:
        import traceback
        error_msg = f"エラー: {str(e)}\n{traceback.format_exc()}"
        st.error(error_msg)
        print(f"TTS Generation Error: {error_msg}")  # Console logging
        return None

# Available voices with descriptions
VOICE_INFO = {
    # 女性声（Female voices）
    "Zephyr": "女性・落ち着いた声",
    "Kore": "女性・明るい声",
    "Aoede": "女性・優しい声",
    "Callirhoe": "女性・上品な声",
    "Autonoe": "女性・元気な声",
    "Despina": "女性・柔らかい声",
    "Erinome": "女性・知的な声",
    "Laomedeia": "女性・穏やかな声",
    "Schedar": "女性・はきはきした声",
    "Pulcherrima": "女性・華やかな声",
    "Vindemiatrix": "女性・深みのある声",
    
    # 男性声（Male voices）
    "Puck": "男性・若々しい声",
    "Charon": "男性・落ち着いた声",
    "Fenrir": "男性・力強い声",
    "Leda": "男性・優しい声",
    "Orus": "男性・渋い声",
    "Enceladus": "男性・重厚な声",
    "Iapetus": "男性・知的な声",
    "Umbriel": "男性・穏やかな声",
    "Algieba": "男性・明瞭な声",
    "Algenib": "男性・はっきりした声",
    "Rasalgethi": "男性・深い声",
    "Achernar": "男性・クリアな声",
    "Alnilam": "男性・温かい声",
    "Gacrux": "男性・しっかりした声",
    "Achird": "男性・親しみやすい声",
    "Zubenelgenubi": "男性・独特な声",
    "Sadachbia": "男性・さわやかな声",
    "Sadaltager": "男性・印象的な声",
    "Sulafar": "男性・個性的な声"
}

VOICE_OPTIONS = list(VOICE_INFO.keys())

# Simple authentication
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Get password from secrets or environment
        try:
            correct_password = st.secrets["APP_PASSWORD"]
        except:
            correct_password = os.environ.get("APP_PASSWORD", "demo123")  # Default for development

        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.text_input(
            "パスワードを入力してください",
            type="password",
            on_change=password_entered,
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error
        st.text_input(
            "パスワードを入力してください",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.error("😕 パスワードが正しくありません")
        return False
    else:
        # Password correct
        return True

# Streamlit App
def main():
    st.set_page_config(
        page_title="Gemini TTS 一括音声生成",
        page_icon="🎙️",
        layout="wide"
    )

    st.title("🎙️ Gemini TTS 一括音声生成ツール")

    # Check authentication
    if not check_password():
        st.stop()

    st.markdown("台本CSVをアップロードして、複数の音声を一括生成します。")

    # Initialize session state
    if 'generated_files' not in st.session_state:
        st.session_state.generated_files = []
    
    # Main content area - Initialize default values early
    default_voice = "Zephyr"  # Default voice
    default_instruction = ""
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📄 台本アップロード")
        
        # CSV template download
        st.markdown("### CSVテンプレート")
        template_data = {
            'text': [
                'おはようございます。本日は晴天なり。',
                '続いて、お知らせです。',
                'ご清聴ありがとうございました。'
            ],
            'voice': ['Zephyr', 'Kore', 'Zephyr'],
            'filename': ['greeting', 'announcement', 'closing'],
            'instruction': [
                '明るく元気な声で',
                'はっきりと聞き取りやすく',
                'ゆっくりと丁寧に'
            ]
        }
        
        template_df = pd.DataFrame(template_data)
        # UTF-8 with BOM for Excel compatibility
        csv_template = template_df.to_csv(index=False, encoding='utf-8-sig')
        
        st.download_button(
            label="📥 CSVテンプレートをダウンロード",
            data=csv_template.encode('utf-8-sig'),
            file_name="tts_template.csv",
            mime="text/csv"
        )
        
        # File uploader
        uploaded_file = st.file_uploader(
            "CSVファイルを選択",
            type=['csv'],
            help="text列は必須です。voice, filename, instruction列は任意です。"
        )
        
        if uploaded_file is not None:
            try:
                # Read CSV - try utf-8-sig first (for Excel), then fallback to utf-8
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
                except:
                    uploaded_file.seek(0)  # Reset file pointer
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                
                # Validate required column
                if 'text' not in df.columns:
                    st.error("❌ CSVファイルに'text'列が必要です。")
                else:
                    # Ensure columns exist (but keep empty values as-is)
                    if 'voice' not in df.columns:
                        df['voice'] = pd.NA
                    if 'filename' not in df.columns:
                        df['filename'] = pd.NA
                    if 'instruction' not in df.columns:
                        df['instruction'] = pd.NA
                    
                    # Display preview
                    st.success(f"✅ {len(df)}件のテキストを読み込みました。")
                    st.dataframe(df, height=300)
                    
                    # Store in session state
                    st.session_state.df = df
                    
            except Exception as e:
                st.error(f"CSVファイルの読み込みエラー: {str(e)}")
    
    with col2:
        st.header("🎵 音声生成")
        
        # Default settings section
        st.subheader("📊 デフォルト設定")
        
        # Model selector
        model_options = [
            "gemini-2.5-flash-preview-tts",
            "gemini-2.5-pro-preview-tts"
        ]
        default_model = st.selectbox(
            "TTSモデル",
            model_options,
            index=0,  # Default to Flash
            help="Flash: 高速・軽量 / Pro: 高品質・高精度"
        )
        
        # Voice selector with descriptions
        voice_display_options = [f"{voice} ({desc})" for voice, desc in VOICE_INFO.items()]
        selected_voice_display = st.selectbox(
            "デフォルト話者",
            voice_display_options,
            index=0,
            help="生成する音声の話者を選択します。カッコ内は声の特徴です。"
        )
        # Extract voice name from display string
        default_voice = selected_voice_display.split(" (")[0]
        
        # Default instruction
        default_instruction = st.text_area(
            "全体の演技指示",
            value="",
            height=80,
            help="例: 明るく元気な声で読む、ゆっくりと落ち着いた声で読む、など",
            placeholder="全体の演技指示（任意）"
        )
        
        # Initialize default values for advanced settings
        default_temperature = 1.0
        
        # Advanced settings in expander
        with st.expander("⚙️ 詳細設定", expanded=False):
            default_temperature = st.slider(
                "温度パラメータ",
                min_value=0.1,
                max_value=2.0,
                value=1.0,
                step=0.1,
                help="低い値でより一貫性のある音声、高い値でより多様な音声が生成されます（標準: 1.0）"
            )
        
        st.divider()
        
        if 'df' in st.session_state:
            df = st.session_state.df
            
            # Generation button
            if st.button("🚀 音声を一括生成", type="primary", use_container_width=True):
                client = init_client()
                
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                generated_files = []
                
                # Create temporary directory
                with tempfile.TemporaryDirectory() as temp_dir:
                    for idx, row in df.iterrows():
                        # Update progress
                        progress = (idx + 1) / len(df)
                        progress_bar.progress(progress)
                        # Get display filename (handle NaN)
                        display_filename = row.get('filename')
                        if pd.isna(display_filename) or str(display_filename).strip() == '':
                            display_filename = f"audio_{idx+1:03d}"
                        status_text.text(f"生成中... ({idx + 1}/{len(df)}) - {display_filename}")
                        
                        # Get actual voice that will be used
                        voice_for_log = row.get('voice')
                        if pd.isna(voice_for_log) or str(voice_for_log).strip() == '':
                            voice_for_log = default_voice
                        
                        # Debug logging
                        print(f"\n🎯 Processing {idx + 1}/{len(df)}: {display_filename}")
                        print(f"   Model: {default_model}")
                        print(f"   Voice: {voice_for_log}")
                        
                        # Skip empty text
                        if pd.isna(row.get('text')) or str(row.get('text')).strip() == '':
                            st.warning(f"行 {idx + 1}: テキストが空のためスキップしました")
                            continue
                        
                        # Combine default and individual instructions
                        combined_instruction = ''
                        if default_instruction:
                            combined_instruction = default_instruction
                        
                        # Check for instruction and handle NaN
                        individual_instruction = row.get('instruction', '')
                        if pd.notna(individual_instruction) and str(individual_instruction).strip():
                            if combined_instruction:
                                combined_instruction += f"\n{individual_instruction}"
                            else:
                                combined_instruction = individual_instruction
                        
                        # Use default values when CSV values are empty/invalid
                        voice_name = row.get('voice')
                        if pd.isna(voice_name) or str(voice_name).strip() == '' or voice_name not in VOICE_OPTIONS:
                            voice_name = default_voice
                        
                        pcm_data = generate_tts(
                            client,
                            row['text'],
                            voice=voice_name,
                            instruction=combined_instruction,
                            temperature=default_temperature,
                            model=default_model
                        )
                        
                        if pcm_data:
                            # Create wave file
                            wave_buffer = create_wave_file(pcm_data)
                            # Use default filename if empty
                            file_base = row.get('filename')
                            if pd.isna(file_base) or str(file_base).strip() == '':
                                file_base = f"audio_{idx+1:03d}"
                            filename = f"{file_base}.wav"
                            
                            # Save to temp directory
                            file_path = os.path.join(temp_dir, filename)
                            with open(file_path, 'wb') as f:
                                f.write(wave_buffer.getvalue())
                            
                            generated_files.append({
                                'filename': filename,
                                'text': row['text'][:50] + '...' if len(row['text']) > 50 else row['text'],
                                'voice': voice_name,  # Use the validated voice name
                                'path': file_path,
                                'data': wave_buffer.getvalue()
                            })
                        
                        # Small delay to avoid rate limiting
                        time.sleep(1.5)
                    
                    # Complete
                    progress_bar.progress(1.0)
                    status_text.text("✅ 生成完了！")
                    
                    # Store results
                    st.session_state.generated_files = generated_files
                    
                    # Create ZIP file
                    if generated_files:
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for file_info in generated_files:
                                zip_file.writestr(file_info['filename'], file_info['data'])
                        
                        zip_buffer.seek(0)
                        st.session_state.zip_data = zip_buffer.getvalue()
            
            # Display results
            if st.session_state.generated_files:
                st.header("📦 生成結果")
                
                # Download all button
                if 'zip_data' in st.session_state:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.download_button(
                        label="📥 すべての音声をZIPでダウンロード",
                        data=st.session_state.zip_data,
                        file_name=f"tts_output_{timestamp}.zip",
                        mime="application/zip",
                        type="primary",
                        use_container_width=True
                    )
                
                # Individual file preview
                st.subheader("個別ファイル")
                for file_info in st.session_state.generated_files:
                    with st.expander(f"🔊 {file_info['filename']}"):
                        st.text(f"テキスト: {file_info['text']}")
                        st.text(f"話者: {file_info['voice']}")
                        st.audio(file_info['data'], format='audio/wav')
                        st.download_button(
                            label="ダウンロード",
                            data=file_info['data'],
                            file_name=file_info['filename'],
                            mime="audio/wav",
                            key=f"download_{file_info['filename']}"
                        )
        else:
            st.info("👈 まずCSVファイルをアップロードしてください。")

if __name__ == "__main__":
    main()