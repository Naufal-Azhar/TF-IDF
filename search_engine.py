import os
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import fitz  # PyMuPDF
from typing import List, Tuple, Optional

class TfidfSearchEngine:
    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.docs = []
        self.filenames = []
        self.vectorizer = TfidfVectorizer(stop_words='english')
        self.doc_vectors = None
        self.last_modified_times = {}  # Track file modification times
        self.load_documents()

    def load_documents(self):
        """Load and index all supported documents from the folder"""
        self.docs = []
        self.filenames = []
        self.last_modified_times = {}
        
        if not os.path.exists(self.folder_path):
            print(f"Warning: Folder path '{self.folder_path}' does not exist.")
            return
        
        print(f"Loading documents from {self.folder_path}...")
        loaded_count = 0
        error_count = 0
        
        # Get all files in directory
        for filename in os.listdir(self.folder_path):
            file_path = os.path.join(self.folder_path, filename)
            
            # Skip directories and unsupported files
            if os.path.isdir(file_path) or not filename.lower().endswith(('.txt', '.pdf')):
                continue
                
            try:
                # Store file modification time
                mod_time = os.path.getmtime(file_path)
                self.last_modified_times[filename] = mod_time
                
                # Read file content based on type
                text = None
                if filename.lower().endswith('.txt'):
                    text = self._read_txt_file(file_path)
                elif filename.lower().endswith('.pdf'):
                    text = self._read_pdf_file(file_path)
                
                if text:
                    self.docs.append(text)
                    self.filenames.append(filename)
                    loaded_count += 1
                    print(f"Loaded: {filename}")
                else:
                    error_count += 1
                    print(f"Failed to read: {filename}")
                    
            except Exception as e:
                error_count += 1
                print(f"Error processing {filename}: {e}")
                continue
        
        # Build TF-IDF index after loading all documents
        if self.docs:
            try:
                print("Building search index...")
                self.doc_vectors = self.vectorizer.fit_transform(self.docs)
                print(f"Successfully indexed {loaded_count} documents.")
                if error_count > 0:
                    print(f"Failed to index {error_count} documents.")
            except Exception as e:
                print(f"Error building search index: {e}")
                self.doc_vectors = None
        else:
            self.doc_vectors = None
            print("No documents available for indexing.")

    def _read_txt_file(self, file_path: str) -> Optional[str]:
        """Read text from a .txt file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
                if not text:
                    print(f"Warning: Empty text file: {file_path}")
                    return None
                return text
        except UnicodeDecodeError:
            print(f"Error: Invalid text encoding in file: {file_path}")
            return None
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None

    def _read_pdf_file(self, file_path: str) -> Optional[str]:
        """Read text from a .pdf file using PyMuPDF"""
        try:
            doc = fitz.open(file_path)
            if doc.page_count == 0:
                print(f"Warning: Empty PDF file: {file_path}")
                doc.close()
                return None
                
            text = ""
            for page_num in range(doc.page_count):
                try:
                    page = doc.load_page(page_num)
                    page_text = page.get_text().strip()
                    text += page_text + "\n"
                except Exception as e:
                    print(f"Warning: Could not read page {page_num} in {file_path}: {e}")
                    continue
                
            doc.close()
            
            if not text.strip():
                print(f"Warning: No text content found in PDF: {file_path}")
                return None
                
            return text
            
        except fitz.FileDataError:
            print(f"Error: Corrupted PDF file: {file_path}")
            return None
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
            return None

    def reload_documents(self):
        """Reload all documents from the folder"""
        print("Reloading documents...")
        self.load_documents()

    def check_for_changes(self) -> bool:
        """Check if any files have been modified, added, or deleted"""
        if not os.path.exists(self.folder_path):
            return False
        
        current_files = set()
        changes_detected = False
        
        # Check existing files for modifications
        for filename in os.listdir(self.folder_path):
            file_path = os.path.join(self.folder_path, filename)
            
            # Skip directories and unsupported files
            if os.path.isdir(file_path) or not (filename.lower().endswith(('.txt', '.pdf'))):
                continue
                
            current_files.add(filename)
            current_mod_time = os.path.getmtime(file_path)
            
            # Check if file is new or modified
            if (filename not in self.last_modified_times or 
                self.last_modified_times[filename] != current_mod_time):
                changes_detected = True
                break
        
        # Check if any files were deleted
        tracked_files = set(self.last_modified_times.keys())
        if tracked_files != current_files:
            changes_detected = True
        
        return changes_detected

    def auto_reload_if_changed(self):
        """Automatically reload documents if changes are detected"""
        if self.check_for_changes():
            print("Changes detected in document folder.")
            self.reload_documents()
            return True
        return False

    def search(self, query: str, top_n: int = 5, auto_reload: bool = True) -> List[Tuple[str, str, float]]:
        """
        Search for documents similar to the query
        
        Args:
            query: Search query string
            top_n: Number of top results to return
            auto_reload: Whether to automatically check for file changes before searching
            
        Returns:
            List of tuples containing (filename, document_text, similarity_score)
        """
        # Optionally check for changes before searching
        if auto_reload:
            self.auto_reload_if_changed()
        
        # Check if we have any documents to search
        if not self.docs or self.doc_vectors is None:
            print("No documents available for search.")
            return []
        
        try:
            query_vector = self.vectorizer.transform([query])
            similarities = cosine_similarity(query_vector, self.doc_vectors).flatten()
            
            results = sorted(
                zip(self.filenames, self.docs, similarities),
                key=lambda x: x[2],
                reverse=True
            )[:top_n]
            
            return results
        except Exception as e:
            print(f"Error during search: {e}")
            return []

    def get_document_count(self) -> int:
        """Get the number of loaded documents"""
        return len(self.docs)

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions"""
        return ['.txt', '.pdf']

    def add_document(self, file_path: str, reload: bool = True) -> bool:
        """
        Add a single document to the search engine
        
        Args:
            file_path: Path to the document file
            reload: Whether to reload all documents after adding
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import shutil
            filename = os.path.basename(file_path)
            destination = os.path.join(self.folder_path, filename)
            
            # Copy file to the search folder
            shutil.copy2(file_path, destination)
            
            if reload:
                self.reload_documents()
            
            print(f"Successfully added document: {filename}")
            return True
        except Exception as e:
            print(f"Error adding document {file_path}: {e}")
            return False

    def remove_document(self, filename: str, reload: bool = True) -> bool:
        """
        Remove a document from the search engine
        
        Args:
            filename: Name of the file to remove
            reload: Whether to reload all documents after removal
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = os.path.join(self.folder_path, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                
                if reload:
                    self.reload_documents()
                
                print(f"Successfully removed document: {filename}")
                return True
            else:
                print(f"Document {filename} not found.")
                return False
        except Exception as e:
            print(f"Error removing document {filename}: {e}")
            return False


# Example usage
if __name__ == "__main__":
    # Initialize the search engine
    search_engine = TfidfSearchEngine("./documents")
    
    # Search for documents
    results = search_engine.search("machine learning algorithms", top_n=3)
    
    print("Search Results:")
    print("-" * 50)
    for i, (filename, content, score) in enumerate(results, 1):
        print(f"{i}. {filename} (Score: {score:.4f})")
        print(f"Preview: {content[:200]}...")
        print("-" * 50)
    
    # Manually reload documents
    search_engine.reload_documents()
    
    # Check for changes without reloading
    if search_engine.check_for_changes():
        print("Changes detected!")
        search_engine.reload_documents()