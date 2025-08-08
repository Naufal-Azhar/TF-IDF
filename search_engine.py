import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class TfidfSearchEngine:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.docs = []
        self.filenames = []
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.doc_vectors = None
        self.load_documents()

    def load_documents(self):
        for filename in os.listdir(self.folder_path):
            if filename.endswith(".txt"):
                path = os.path.join(self.folder_path, filename)
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
                    self.docs.append(text)
                    self.filenames.append(filename)
        self.doc_vectors = self.vectorizer.fit_transform(self.docs)

    def search(self, query, top_n=5):
        query_vector = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, self.doc_vectors).flatten()
        results = sorted(
            zip(self.filenames, self.docs, similarities),
            key=lambda x: x[2],
            reverse=True
        )[:top_n]
        return results
