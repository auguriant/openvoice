import os
import torch
import argparse
import gradio as gr
from zipfile import ZipFile
import langid


parser = argparse.ArgumentParser()
parser.add_argument("--online_checkpoint_url", default="https://myshell-public-repo-hosting.s3.amazonaws.com/checkpoints_1226.zip")
parser.add_argument("--share", action='store_true', default=False, help="make link public")
args = parser.parse_args()

# first download the checkpoints from server
if not os.path.exists('checkpoints/'):
    print('Downloading OpenVoice checkpoint ...')
    os.system(f'wget {args.online_checkpoint_url} -O ckpt.zip')
    print('Extracting OpenVoice checkpoint ...')
    ZipFile("ckpt.zip").extractall()

# Init EN/ZH baseTTS and ToneConvertor
from OpenVoice import se_extractor
from OpenVoice.api import BaseSpeakerTTS, ToneColorConverter

en_ckpt_base = 'checkpoints/base_speakers/EN'
zh_ckpt_base = 'checkpoints/base_speakers/ZH'
ckpt_converter = 'checkpoints/converter'
device = 'cuda' if torch.cuda.is_available() else 'cpu'
output_dir = 'outputs'
os.makedirs(output_dir, exist_ok=True)
en_base_speaker_tts = BaseSpeakerTTS(f'{en_ckpt_base}/config.json', device=device)
en_base_speaker_tts.load_ckpt(f'{en_ckpt_base}/checkpoint.pth')
zh_base_speaker_tts = BaseSpeakerTTS(f'{zh_ckpt_base}/config.json', device=device)
zh_base_speaker_tts.load_ckpt(f'{zh_ckpt_base}/checkpoint.pth')
tone_color_converter = ToneColorConverter(f'{ckpt_converter}/config.json', device=device)
tone_color_converter.load_ckpt(f'{ckpt_converter}/checkpoint.pth')
en_source_default_se = torch.load(f'{en_ckpt_base}/en_default_se.pth').to(device)
en_source_style_se = torch.load(f'{en_ckpt_base}/en_style_se.pth').to(device)
zh_source_se = torch.load(f'{zh_ckpt_base}/zh_default_se.pth').to(device)

supported_languages = ['zh', 'en']

def predict(prompt, style, audio_file_pth, mic_file_path, use_mic, agree):
    # initialize a empty info
    text_hint = ''
    # agree with the terms
    if agree == False:
        text_hint += '[ERROR] Please accept the Terms & Condition!\n'
        gr.Warning("Please accept the Terms & Condition!")
        return (
            text_hint,
            None,
            None,
        )

    # first detect the input language
    language_predicted = langid.classify(prompt)[0].strip()  
    print(f"Detected language:{language_predicted}")

    if language_predicted not in supported_languages:
        text_hint += f"[ERROR] The detected language {language_predicted} for your input text is not in our Supported Languages: {supported_languages}\n"
        gr.Warning(
            f"The detected language {language_predicted} for your input text is not in our Supported Languages: {supported_languages}"
        )

        return (
            text_hint,
            None,
            None,
        )
    
    if language_predicted == "zh":
        tts_model = zh_base_speaker_tts
        source_se = zh_source_se
        language = 'Chinese'
        if style not in ['default']:
            text_hint += f"[ERROR] The style {style} is not supported for Chinese, which should be in ['default']\n"
            gr.Warning(f"The style {style} is not supported for Chinese, which should be in ['default']")
            return (
                text_hint,
                None,
                None,
            )

    else:
        tts_model = en_base_speaker_tts
        if style == 'default':
            source_se = en_source_default_se
        else:
            source_se = en_source_style_se
        language = 'English'
        if style not in ['default', 'whispering', 'shouting', 'excited', 'cheerful', 'terrified', 'angry', 'sad', 'friendly']:
            text_hint += f"[ERROR] The style {style} is not supported for English, which should be in ['default', 'whispering', 'shouting', 'excited', 'cheerful', 'terrified', 'angry', 'sad', 'friendly']\n"
            gr.Warning(f"The style {style} is not supported for English, which should be in ['default', 'whispering', 'shouting', 'excited', 'cheerful', 'terrified', 'angry', 'sad', 'friendly']")
            return (
                text_hint,
                None,
                None,
            )

    if use_mic == True:
        if mic_file_path is not None:
            speaker_wav = mic_file_path
        else:
            text_hint += f"[ERROR] Please record your voice with Microphone, or uncheck Use Microphone to use reference audios\n"
            gr.Warning(
                "Please record your voice with Microphone, or uncheck Use Microphone to use reference audios"
            )
            return (
                text_hint,
                None,
                None,
            )

    else:
        speaker_wav = audio_file_pth

    if len(prompt) < 2:
        text_hint += f"[ERROR] Please give a longer prompt text \n"
        gr.Warning("Please give a longer prompt text")
        return (
            text_hint,
            None,
            None,
        )
    if len(prompt) > 200:
        text_hint += f"[ERROR] Text length limited to 200 characters for this demo, please try shorter text. You can clone our open-source repo and try for your usage \n"
        gr.Warning(
            "Text length limited to 200 characters for this demo, please try shorter text. You can clone our open-source repo for your usage"
        )
        return (
            text_hint,
            None,
            None,
        )
    
    # note diffusion_conditioning not used on hifigan (default mode), it will be empty but need to pass it to model.inference
    try:
        target_se, wavs_folder = se_extractor.get_se(speaker_wav, tone_color_converter, target_dir='processed', max_length=60., vad=True)
        # os.system(f'rm -rf {wavs_folder}')
    except Exception as e:
        text_hint += f"[ERROR] Get target tone color error {str(e)} \n"
        gr.Warning(
            "[ERROR] Get target tone color error {str(e)} \n"
        )
        return (
            text_hint,
            None,
            None,
        )

    src_path = f'{output_dir}/tmp.wav'
    tts_model.tts(prompt, src_path, speaker=style, language=language)

    save_path = f'{output_dir}/output.wav'
    # Run the tone color converter
    encode_message = "@MyShell"
    tone_color_converter.convert(
        audio_src_path=src_path, 
        src_se=source_se, 
        tgt_se=target_se, 
        output_path=save_path,
        message=encode_message)

    text_hint += f'''Get response successfully \n'''

    return (
        text_hint,
        save_path,
        speaker_wav,
    )



title = "OpenVoice"

description = """
We introduce OpenVoice, a versatile instant voice cloning approach that requires only a short audio clip from the reference speaker to replicate their voice and generate speech in multiple languages. OpenVoice enables granular control over voice styles, including emotion, accent, rhythm, pauses, and intonation, in addition to replicating the tone color of the reference speaker. OpenVoice also achieves zero-shot cross-lingual voice cloning for languages not included in the massive-speaker training set.
"""
wrapped_markdown_content = f"<div style='border: 1px solid #000; padding: 10px;'>{content}</div>"


examples = [
    [
        "今天天气真好，我们一起出去吃饭吧。",
        'default',
        "examples/speaker0.mp3",
        None,
        False,
        True,
    ],[
        "This audio is generated by open voice with a half-performance model.",
        'whispering',
        "examples/speaker1.mp3",
        None,
        False,
        True,
    ],
    [
        "He hoped there would be stew for dinner, turnips and carrots and bruised potatoes and fat mutton pieces to be ladled out in thick, peppered, flour-fattened sauce.",
        'sad',
        "examples/speaker2.mp3",
        None,
        False,
        True,
    ],
]

with gr.Blocks(analytics_enabled=False) as demo:

    with gr.Row():
        with gr.Column():
            with gr.Row():
                gr.Markdown(
                    """
                    ## <img src="https://huggingface.co/spaces/myshell-ai/OpenVoice/raw/main/logo.jpg" height="40"/>
                    """
                )
            with gr.Row():    
                gr.Markdown(markdown_table_v2)
            with gr.Row():
                gr.Markdown(description)
        with gr.Column():
            gr.Video('./open_voice.mp4', autoplay=True)
            
    with gr.Row():
        gr.HTML(wrapped_markdown_content)

    with gr.Row():
        with gr.Column():
            input_text_gr = gr.Textbox(
                label="Text Prompt",
                info="One or two sentences at a time is better. Up to 200 text characters.",
                value="He hoped there would be stew for dinner, turnips and carrots and bruised potatoes and fat mutton pieces to be ladled out in thick, peppered, flour-fattened sauce.",
            )
            style_gr = gr.Dropdown(
                label="Style",
                info="Select a style of output audio for the synthesised speech. (Chinese only support 'default' now)",
                choices=['default', 'whispering', 'cheerful', 'terrified', 'angry', 'sad', 'friendly'],
                max_choices=1,
                value="default",
            )
            ref_gr = gr.Audio(
                label="Reference Audio",
                info="Click on the ✎ button to upload your own target speaker audio",
                type="filepath",
                value="examples/speaker0.mp3",
            )
            mic_gr = gr.Audio(
                source="microphone",
                type="filepath",
                info="Use your microphone to record audio",
                label="Use Microphone for Reference",
            )
            use_mic_gr = gr.Checkbox(
                label="Use Microphone",
                value=False,
                info="Notice: Microphone input may not work properly under traffic",
            )
            tos_gr = gr.Checkbox(
                label="Agree",
                value=False,
                info="I agree to the terms of the cc-by-nc-4.0 license-: https://github.com/myshell-ai/OpenVoice/blob/main/LICENSE",
            )

            tts_button = gr.Button("Send", elem_id="send-btn", visible=True)


        with gr.Column():
            out_text_gr = gr.Text(label="Info")
            audio_gr = gr.Audio(label="Synthesised Audio", autoplay=True)
            ref_audio_gr = gr.Audio(label="Reference Audio Used")

            gr.Examples(examples,
                        label="Examples",
                        inputs=[input_text_gr, style_gr, ref_gr, mic_gr, use_mic_gr, tos_gr],
                        outputs=[out_text_gr, audio_gr, ref_audio_gr],
                        fn=predict,
                        cache_examples=False,)
            tts_button.click(predict, [input_text_gr, style_gr, ref_gr, mic_gr, use_mic_gr, tos_gr], outputs=[out_text_gr, audio_gr, ref_audio_gr])

demo.queue()  
demo.launch(debug=True, show_api=True, share=args.share)