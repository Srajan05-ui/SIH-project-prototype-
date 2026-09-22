import ollama
import logging

logger = logging.getLogger(__name__)

class LocalRAGDesk:
    def __init__(self, model_name='llama3.1:8b'):
        self.model_name = model_name
        self.context_store = []
        
    def add_context(self, document_text: str):
        """Adds verified internal string data to the local RAG context store."""
        if document_text and document_text not in self.context_store:
            self.context_store.append(document_text)
            
    def query(self, user_question: str) -> str:
        """
        Builds a structured prompt matrix with local context and queries the Ollama model.
        Returns a private evaluation summary securely locally.
        """
        if not user_question.strip():
            return "Please provide a valid query."
            
        context_str = "\n".join(self.context_store)
        prompt = (
            "You are a Principal AI Policy Analyst for the National Airfare Intelligence Platform. "
            "Use the following verified internal context to answer the user's question securely. "
            "If the answer is not in the context, do not guess.\n\n"
            f"Context:\n{context_str}\n\n"
            f"Question: {user_question}\n"
            "Answer:"
        )
        
        try:
            response = ollama.chat(model=self.model_name, messages=[
                {
                    'role': 'user',
                    'content': prompt
                }
            ])
            return response.get('message', {}).get('content', "No response generated.")
        except Exception as e:
            logger.error(f"Ollama local RAG query failed: {e}")
            return f"Error connecting to local RAG model '{self.model_name}'. Ensure Ollama is running. Error: {e}"
