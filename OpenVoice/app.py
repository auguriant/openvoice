import os
import gradio as gr
import requests
import langid
import base64
import json
import time

API_URL = os.environ.get("API_URL")
supported_languages = ['zh', 'en']

output_dir = 'outputs'
os.makedirs(output_dir, exist_ok=True)

def audio_to_base64(audio_file):
    with open(audio_file, "rb") as audio_file:
        audio_data = audio_file.read()
        base64_data = base64.b64encode(audio_data).decode("utf-8")
    return base64_data

def predict(prompt, style, audio_file_pth, agree):
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

    if language_predicted == "en":
        if style not in ['default', 'whispering', 'shouting', 'excited', 'cheerful', 'terrified', 'angry', 'sad', 'friendly']:
            text_hint += f"[ERROR] The style {style} is not supported for English, which should be in ['default', 'whispering', 'shouting', 'excited', 'cheerful', 'terrified', 'angry', 'sad', 'friendly']\n"
            gr.Warning(f"The style {style} is not supported for English, which should be in ['default', 'whispering', 'shouting', 'excited', 'cheerful', 'terrified', 'angry', 'sad', 'friendly']")
            return (
                text_hint,
                None,
                None,
            )
        style = 'en_' + style
        prompt_length = len(prompt.split(' '))

    else:
        if style not in ['default']:
            text_hint += f"[ERROR] The style {style} is not supported for Chinese, which should be in ['default']\n"
            gr.Warning(f"The style {style} is not supported for Chinese, which should be in ['default']")
            return (
                text_hint,
                None,
                None,
            )
        style = 'cn_' + style
        prompt_length = len(prompt)

    speaker_wav = audio_file_pth

    if prompt_length < 2:
        text_hint += f"[ERROR] Please give a longer prompt text \n"
        gr.Warning("Please give a longer prompt text")
        return (
            text_hint,
            None,
            None,
        )
    if prompt_length > 50:
        text_hint += f"[ERROR] Text length limited to 50 words for this demo, please try shorter text. You can clone our open-source repo and try for your usage \n"
        gr.Warning(
            "Text length limited to 50 words for this demo, please try shorter text. You can clone our open-source repo for your usage"
        )
        return (
            text_hint,
            None,
            None,
        )

    save_path = f'{output_dir}/output.wav'
    speaker_audio_base64 = audio_to_base64(speaker_wav)
    data = {
        "text": prompt,
        "reference_speaker": speaker_audio_base64,
        "emotion": style
    }
    
    start = time.time()
    # Send the data as a POST request
    response = requests.post(API_URL, json=data, timeout=60)
    print(f'Get response successfully within {time.time() - start}')

    # Check the response
    if response.status_code == 200:
        try:
            json_data = json.loads(response.content)
            text_hint += f"[ERROR] {json_data['error']} \n"
            gr.Warning(
                f"[ERROR] {json_data['error']} \n"
            )
            return (
                text_hint,
                None,
                None,
            )
        except:
            with open(save_path, 'wb') as f:
                f.write(response.content)
    else:
        text_hint += f"[HTTP ERROR] {response.status_code} - {response.text} \n"
        gr.Warning(
            f"[HTTP ERROR] {response.status_code} - {response.text} \n"
        )
        return (
            text_hint,
            None,
            None,
        )
    text_hint += f'''Get response successfully \n'''
    return (
        text_hint,
        save_path,
        speaker_wav,
    )


title = "MyShell OpenVoice"

description = """
We introduce OpenVoice, a versatile instant voice cloning approach that requires only a short audio clip from the reference speaker to replicate their voice and generate speech in multiple languages. OpenVoice enables granular control over voice styles, including emotion, accent, rhythm, pauses, and intonation, in addition to replicating the tone color of the reference speaker. OpenVoice also achieves zero-shot cross-lingual voice cloning for languages not included in the massive-speaker training set.
"""

markdown_table = """
<div align="center" style="margin-bottom: 10px;">

|               |               |               |
| :-----------: | :-----------: | :-----------: | 
| **OpenSource Repo** | **Project Page** | **Join the Community** |        
| <div style='text-align: center;'><a style="display:inline-block,align:center" href='https://github.com/myshell-ai/OpenVoice'><img src='https://img.shields.io/github/stars/myshell-ai/OpenVoice?style=social' /></a></div> | [OpenVoice](https://research.myshell.ai/open-voice) | [![Discord](https://img.shields.io/discord/1122227993805336617?color=%239B59B6&label=%20Discord%20)](https://discord.gg/myshell) |

</div>
"""

markdown_table_v2 = """
<div align="center" style="margin-bottom: 2px;">

|               |               |               |              |
| :-----------: | :-----------: | :-----------: | :-----------: | 
| **Github Repo** | <div style='text-align: center;'><a style="display:inline-block,align:center" href='https://github.com/myshell-ai/OpenVoice'><img src='https://img.shields.io/github/stars/myshell-ai/OpenVoice?style=social' /></a></div> |  **Project Page** |  [OpenVoice](https://research.myshell.ai/open-voice) |     

| | |
| :-----------: | :-----------: |
**Join the Community** |   [![Discord](https://img.shields.io/discord/1122227993805336617?color=%239B59B6&label=%20Discord%20)](https://discord.gg/myshell) |

</div>
"""
content = """
<div>
  <strong>If the generated voice does not sound like the reference voice, please refer to <a href='https://github.com/myshell-ai/OpenVoice/blob/main/docs/QA.md'>this QnA</a>.</strong> <strong>For multi-lingual & cross-lingual examples, please refer to <a href='https://github.com/myshell-ai/OpenVoice/blob/main/demo_part2.ipynb'>this jupyter notebook</a>.</strong>
  This online demo mainly supports <strong>English</strong>. The <em>default</em> style also supports <strong>Chinese</strong>. But OpenVoice can adapt to any other language as long as a base speaker is provided.
</div>
"""
wrapped_markdown_content = f"<div style='border: 1px solid #000; padding: 10px;'>{content}</div>"


examples = [
    [
        "今天天气真好，我们一起出去吃饭吧。",
        'default',
        "examples/speaker1.mp3",
        True,
    ],[
        "This audio is generated by open voice with a half-performance model.",
        'whispering',
        "examples/speaker2.mp3",
        True,
    ],
    [
        "He hoped there would be stew for dinner, turnips and carrots and bruised potatoes and fat mutton pieces to be ladled out in thick, peppered, flour-fattened sauce.",
        'sad',
        "examples/speaker0.mp3",
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
                value="examples/speaker2.mp3",
            )
            tos_gr = gr.Checkbox(
                label="Agree",
                value=False,
                info="I agree to the terms of the MIT license-: https://github.com/myshell-ai/OpenVoice/blob/main/LICENSE",
            )

            tts_button = gr.Button("Send", elem_id="send-btn", visible=True)


        with gr.Column():
            out_text_gr = gr.Text(label="Info")
            audio_gr = gr.Audio(label="Synthesised Audio", autoplay=True)
            ref_audio_gr = gr.Audio(label="Reference Audio Used")

            gr.Examples(examples,
                        label="Examples",
                        inputs=[input_text_gr, style_gr, ref_gr, tos_gr],
                        outputs=[out_text_gr, audio_gr, ref_audio_gr],
                        fn=predict,
                        cache_examples=False,)
            tts_button.click(predict, [input_text_gr, style_gr, ref_gr, tos_gr], outputs=[out_text_gr, audio_gr, ref_audio_gr])

demo.queue(concurrency_count=6)  
demo.launch(debug=True, show_api=True)