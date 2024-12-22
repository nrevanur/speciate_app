import asyncio
import json
import os
import websockets

import requests
import streamlit as st

class Config:
    BASE_URL = "api.speciate.com" if os.getenv("ENV", "prod") == "prod" else "dev.api.speciate.com"
    CONFIG_URL = f"https://{BASE_URL}/v1/configs/"
    CHAT_URL = f"wss://{BASE_URL}/v1/chat-agents/chat-message"
    SAVE_CHAT_URL = f"https://{BASE_URL}/v1/logs"

    LLM_CONTEXT_LOG_COUNT = 10

    LLM_MODEL_NAME = "claude-3-5-sonnet-20241022"


class StreamlitApp:
    def __init__(self):
        self.user_id = st.query_params.get("user_id")
        self.chat_id = st.query_params.get("chat_id")
        self.stream_response_flag = True
        self.connection_url = f"{Config.CHAT_URL}?user_id={self.user_id}&stream_response={self.stream_response_flag}"
        
        if "messages" not in st.session_state:
            st.session_state.messages = [
                {'role': "user", "content": ""},
                {'role': "assistant", "content": "Understood"},
            ]

    def display_title(self):
        st.title("Chat with Speciate Agent")
        hide_decoration_bar_style = '''
            <style>
                header {visibility: hidden;}
            </style>
        '''
        st.markdown(hide_decoration_bar_style, unsafe_allow_html=True)

    def display_config(self):
        response = requests.get(Config.CONFIG_URL)
        if response.ok:
            config_parent = json.loads(response.content)
            config = config_parent['config']
            container = st.container(border=True)
            container.write("Model: " + ":blue["+config['LLM.MODEL_NAME']+"]")
            if self.user_id and self.chat_id:
                container.write(f"Reading :blue[{str(config['LLM.CONTEXT_LOG_COUNT'])}] most recent logs")
            else:
                container.write("No user context available")

    def display_chat_conversation(self):
        # Display user and assistant messages skipping the first two
        for message in st.session_state.messages[2:]:
            # ignore tool use blocks
            if isinstance(message["content"], str):
                st.chat_message(message["role"]).markdown(message["content"])

    def save_chat(self):
        chat_thread = ""
        for message in st.session_state.messages[2:]:  # exclude the first two messages
            if message["role"] == "user":
                chat_thread += f"Me:\n\n{message['content']}\n\n"
            else:
                chat_thread += f"Speciate:\n\n{message['content']}\n\n"

        response = requests.put(
            Config.SAVE_CHAT_URL,
            data=json.dumps({
                "user_id": self.user_id,
                "obs_id": self.chat_id,
                "content": chat_thread
            })
        )
        return response.status_code

    async def handle_chat_response(self, chat_request, chat_response_placeholder):
        try:
            async with websockets.connect(self.connection_url) as websocket:
                await websocket.send(chat_request)

                full_chat_response = ""
                while True:
                    chat_response = await websocket.recv()
                    if chat_response == "END_OF_STREAM_RESPONSE":
                        break
                    full_chat_response += chat_response
                    chat_response_placeholder.markdown(full_chat_response)
                    if self.stream_response_flag == False:
                        break
                return full_chat_response    
        except Exception as e:
            print(str(e))

    async def handle_chat_conversation(self):
        if chat_request := st.chat_input("How can I help you today?"):
            st.chat_message("user").markdown(chat_request)
            st.session_state.messages.append({"role": "user", "content": chat_request})

            with st.chat_message("assistant"):
                with st.spinner("Thinking aloud..."):
                    chat_response_placeholder = st.empty()
                    full_chat_response = await self.handle_chat_response(chat_request, chat_response_placeholder)
                    st.session_state.messages.append({"role": "assistant", "content": full_chat_response})
            
            self.save_chat()
    

if __name__ == "__main__":
    app = StreamlitApp()
    app.display_title()
    app.display_config()
    if app.user_id and app.chat_id:
        app.display_chat_conversation()
        asyncio.run(app.handle_chat_conversation())
