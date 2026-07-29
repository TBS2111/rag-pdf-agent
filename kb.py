import os
import chromadb
from pypdf import PdfReader

class KnowledgeBase:
    def __init__(self, persistent_path: str = "chroma_db", similarity_threshold: float = 0.2):
        self.client = chromadb.PersistentClient(path=persistent_path)
        self.collection = self.client.get_or_create_collection(name="qa_cache")
        self.similarity_threshold = similarity_threshold

    def search(self, question: str):
        """Searches the cache for an exact or semantically similar question."""
        results = self.collection.query(
            query_texts=[question],
            n_results=1,
            where={"type": "qa"}
        )

        if results and results.get("distances") and results["distances"][0]:
            distance = results["distances"][0][0]
            if distance <= self.similarity_threshold:
                matched_doc = results["documents"][0][0]
                metadata = results["metadatas"][0][0]
                return {
                    "matched_question": matched_doc,
                    "answer": metadata.get("answer"),
                    "distance": distance
                }
        return None

    def add(self, question: str, answer: str):
        """Adds a Question-Answer pair to the semantic cache."""
        doc_id = f"qa_{hash(question)}"
        self.collection.add(
            documents=[question],
            metadatas=[{"answer": answer, "type": "qa"}],
            ids=[doc_id]
        )

    def add_pdf(self, file_path: str, chunk_size: int = 800, overlap: int = 100) -> int:
        """Extracts text from a PDF, splits it into overlapping chunks, and stores them in ChromaDB."""
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"

        if not text.strip():
            return 0

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap

        base_name = os.path.basename(file_path)
        for i, chunk in enumerate(chunks):
            chunk_id = f"pdf_{hash(base_name)}_{i}"
            self.collection.add(
                documents=[chunk],
                metadatas=[{"source": base_name, "type": "pdf_chunk"}],
                ids=[chunk_id]
            )

        return len(chunks)

    def retrieve_pdf_context(self, question: str, n_results: int = 3, max_distance: float = 1.5) -> list[str]:
        """Retrieves top-N PDF chunks if they meet the revised distance threshold (1.5)."""
        results = self.collection.query(
            query_texts=[question],
            n_results=n_results,
            where={"type": "pdf_chunk"}
        )

        relevant_chunks = []
        if results and results.get("documents") and results.get("distances") and results["documents"][0]:
            docs = results["documents"][0]
            distances = results["distances"][0]

            for doc, dist in zip(docs, distances):
                if dist <= max_distance:
                    relevant_chunks.append(doc)

        return relevant_chunks

    def stats(self):
        """Returns total items stored in the collection."""
        return {"total_entries": self.collection.count()}

    def clear(self):
        """Resets the collection."""
        self.client.delete_collection(name="qa_cache")
        self.collection = self.client.get_or_create_collection(name="qa_cache")