import os
import pickle
from flask import Flask, request, jsonify, send_from_directory
from langchain_google_genai import ChatGoogleGenerativeAI, HarmBlockThreshold, HarmCategory
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

app = Flask(__name__)

class QueryHandler:
    def __init__(self):
        self.db = None
        self.llm = None
        self.last_modified_time = 0
        self.load_resources()

    def load_resources(self):
        try:
            db_file_path = "db.pkl"
            if os.path.exists(db_file_path):
                self.last_modified_time = os.path.getmtime(db_file_path)
                with open(db_file_path, "rb") as f:
                    self.db = pickle.load(f)
            else:
                self.db = None 
            os.environ["GOOGLE_API_KEY"] = "AIzaSyBk9AIIIZ2GzX4Jsclq-zY4Hqzh2l9m36s"
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                safety_settings={
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
        except Exception as e:
            raise RuntimeError(f"Failed to load resources: {str(e)}")

    def handle_query(self, query):
        try:
            db_file_path = "db.pkl"
            if os.path.exists(db_file_path):
                modified_time = os.path.getmtime(db_file_path)
                if modified_time != self.last_modified_time:
                    self.load_resources()
                    self.last_modified_time = modified_time
            else:
                return "No data found"
            content = "\n".join([x.page_content for x in self.db.similarity_search(query)]) if self.db else ""
            qa_prompt = "Use the following pieces of context to answer the user's question. If you don't know the answer, just say that you don't know, don't try to make up an answer.----------------"
            return self.llm.invoke(qa_prompt + "\nContext:" + content + "\nUser question:\n" + query).content.replace("\n", " ")
        except Exception as e:
            raise RuntimeError(f"An error occurred: {str(e)}")

query_handler = QueryHandler()

@app.route("/")
def home():
    return send_from_directory("", "index.html")

@app.route("/upload")
def upload():
    return send_from_directory("", "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory("", path)

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'message': 'No file part in the request'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), 400

        if file:
            file_path = os.path.join(os.getcwd(), "pdf_db.pdf")
            file.save(file_path)
            db_file_path = os.path.join(os.getcwd(), "db.pkl")
            if os.path.exists(db_file_path):
                os.remove(db_file_path)
            with open(db_file_path, "wb") as f:
                pickle.dump(FAISS.from_documents(PyPDFLoader(file_path).load_and_split(), HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")), f)
            if os.path.exists(db_file_path):
                return jsonify({'message': 'File created successfully'}), 201
    except Exception as e:
        return jsonify({'message': 'Error occurred', 'error': str(e)}), 500
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app.route('/query', methods=['POST'])
def query_docs():
    try:
        return jsonify({'response': query_handler.handle_query(request.json.get('query'))})
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# if __name__ == '__main__':
#     app.run()
