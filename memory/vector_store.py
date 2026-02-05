# memory/vector_store.py
"""
Vector Memory Store for Agent Long-Term Memory
===============================================
Enables agents to remember and learn from past interactions using
semantic search over vector embeddings.

Key capabilities:
- Store interaction history
- Retrieve relevant memories by semantic similarity
- Learn user preferences over time
- Remember successful strategies
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
import json
import os
import ssl
from pathlib import Path

# Disable SSL verification for corporate environments with proxy/firewall
try:
    ssl._create_default_https_context = ssl._create_unverified_context
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['REQUESTS_CA_BUNDLE'] = ''
except:
    pass

# Force fallback mode to avoid ChromaDB SSL issues
import os

# Allow runtime override to use ChromaDB even if available. Set USE_CHROMADB=1 to enable.
FORCE_FALLBACK = not bool(os.environ.get('USE_CHROMADB'))

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True and not FORCE_FALLBACK
except ImportError:
    CHROMADB_AVAILABLE = False
    
if not CHROMADB_AVAILABLE:
    print("[INFO] Using JSON fallback storage for memory (SSL-safe mode).")


class MemoryType(str, Enum):
    """Types of memories agents can store"""
    INTERACTION = "interaction"  # User interactions
    PREFERENCE = "preference"    # Learned preferences
    STRATEGY = "strategy"        # Successful approaches
    CONTEXT = "context"          # Domain knowledge
    FEEDBACK = "feedback"        # User feedback on actions


@dataclass
class Memory:
    """A single memory entry"""
    memory_id: str
    content: str
    memory_type: MemoryType
    agent_name: str
    metadata: Dict[str, Any]
    timestamp: str
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "memory_type": self.memory_type,
            "agent_name": self.agent_name,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class AgentMemory:
    """
    Long-term memory for agents using vector embeddings
    
    Enables semantic search over past interactions to:
    - Recall relevant context
    - Learn user preferences
    - Remember successful patterns
    - Personalize responses
    """
    
    def __init__(
        self,
        agent_name: str,
        persist_dir: str = "./chroma_db",
        use_fallback: bool = None
    ):
        self.agent_name = agent_name
        self.persist_dir = Path(persist_dir)
        
        # Determine if we should use ChromaDB or fallback
        self.use_chromadb = CHROMADB_AVAILABLE and (use_fallback is not True)
        
        if self.use_chromadb:
            self._init_chromadb()
        else:
            self._init_fallback()
    
    def _init_chromadb(self):
        """Initialize ChromaDB for vector storage"""
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        
        # Create collection for this agent
        self.collection = self.client.get_or_create_collection(
            name=f"{self.agent_name}_memory",
            metadata={
                "description": f"Long-term memory for {self.agent_name}",
                "created": datetime.utcnow().isoformat()
            }
        )
        
        print(f"[OK] ChromaDB memory initialized for {self.agent_name}")
    
    def _init_fallback(self):
        """Initialize simple JSON fallback storage"""
        self.memory_file = self.persist_dir / f"{self.agent_name}_memory.json"
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        if self.memory_file.exists():
            self.memories = json.loads(self.memory_file.read_text(encoding="utf-8"))
        else:
            self.memories = []
        
        print(f"[OK] Fallback memory initialized for {self.agent_name}")
    
    def remember(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.INTERACTION,
        metadata: Dict[str, Any] = None,
        memory_id: str = None
    ) -> str:
        """
        Store a new memory
        
        Args:
            content: The content to remember (will be embedded)
            memory_type: Type of memory
            metadata: Additional structured data
            memory_id: Optional custom ID
        
        Returns:
            Memory ID
        """
        memory_id = memory_id or f"mem_{self.agent_name}_{int(datetime.utcnow().timestamp() * 1000)}"
        
        memory_data = {
            "agent": self.agent_name,
            "type": memory_type,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {})
        }
        
        if self.use_chromadb:
            # Store in ChromaDB with automatic embedding
            self.collection.add(
                documents=[content],
                metadatas=[memory_data],
                ids=[memory_id]
            )
        else:
            # Store in fallback JSON
            self.memories.append({
                "memory_id": memory_id,
                "content": content,
                "metadata": memory_data
            })
            self._save_fallback()
        
        return memory_id
    
    def recall(
        self,
        query: str,
        n_results: int = 5,
        memory_type: Optional[MemoryType] = None,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories by semantic similarity
        
        Args:
            query: What to search for (natural language)
            n_results: Number of results to return
            memory_type: Filter by memory type
            filters: Additional metadata filters
        
        Returns:
            List of relevant memories with metadata
        """
        where_filter = {}
        if memory_type:
            where_filter["type"] = memory_type
        if filters:
            where_filter.update(filters)
        
        if self.use_chromadb:
            # Semantic search using embeddings
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter if where_filter else None
            )
            
            if not results["documents"][0]:
                return []
            
            return [
                {
                    "memory_id": mem_id,
                    "content": doc,
                    "metadata": meta,
                    "relevance": 1.0 - dist  # Convert distance to relevance score
                }
                for mem_id, doc, meta, dist in zip(
                    results["ids"][0],
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )
            ]
        else:
            # Fallback: Simple keyword search
            query_lower = query.lower()
            matches = []
            
            for memory in self.memories:
                content = memory["content"].lower()
                
                # Check if query terms appear in content
                score = sum(1 for word in query_lower.split() if word in content)
                
                if score > 0:
                    # Check filters
                    if memory_type and memory["metadata"].get("type") != memory_type:
                        continue
                    
                    matches.append({
                        "memory_id": memory["memory_id"],
                        "content": memory["content"],
                        "metadata": memory["metadata"],
                        "relevance": score / len(query_lower.split())
                    })
            
            # Sort by relevance and return top N
            matches.sort(key=lambda x: x["relevance"], reverse=True)
            return matches[:n_results]
    
    def forget(self, memory_id: str):
        """Delete a specific memory"""
        if self.use_chromadb:
            self.collection.delete(ids=[memory_id])
        else:
            self.memories = [m for m in self.memories if m["memory_id"] != memory_id]
            self._save_fallback()
    
    def get_recent(self, n: int = 10, memory_type: Optional[MemoryType] = None) -> List[Dict[str, Any]]:
        """Get N most recent memories"""
        if self.use_chromadb:
            where = {"type": memory_type} if memory_type else None
            results = self.collection.get(
                where=where,
                limit=n
            )
            
            if not results["documents"]:
                return []
            
            return [
                {
                    "memory_id": mem_id,
                    "content": doc,
                    "metadata": meta
                }
                for mem_id, doc, meta in zip(
                    results["ids"],
                    results["documents"],
                    results["metadatas"]
                )
            ]
        else:
            filtered = self.memories
            if memory_type:
                filtered = [m for m in self.memories if m["metadata"].get("type") == memory_type]
            
            # Sort by timestamp (most recent first)
            filtered.sort(key=lambda x: x["metadata"].get("timestamp", ""), reverse=True)
            return filtered[:n]
    
    def count(self, memory_type: Optional[MemoryType] = None) -> int:
        """Count memories"""
        if self.use_chromadb:
            if memory_type:
                results = self.collection.get(where={"type": memory_type})
                return len(results["ids"])
            else:
                return self.collection.count()
        else:
            if memory_type:
                return len([m for m in self.memories if m["metadata"].get("type") == memory_type])
            return len(self.memories)
    
    def clear(self, memory_type: Optional[MemoryType] = None):
        """Clear all memories (or specific type)"""
        if self.use_chromadb:
            if memory_type:
                # Delete by type
                results = self.collection.get(where={"type": memory_type})
                if results["ids"]:
                    self.collection.delete(ids=results["ids"])
            else:
                # Delete collection and recreate
                self.client.delete_collection(self.collection.name)
                self._init_chromadb()
        else:
            if memory_type:
                self.memories = [m for m in self.memories if m["metadata"].get("type") != memory_type]
            else:
                self.memories = []
            self._save_fallback()
    
    def _save_fallback(self):
        """Save fallback memories to disk"""
        if not self.use_chromadb:
            self.memory_file.write_text(
                json.dumps(self.memories, indent=2),
                encoding="utf-8"
            )
    
    def export(self) -> List[Dict[str, Any]]:
        """Export all memories as JSON"""
        if self.use_chromadb:
            results = self.collection.get()
            return [
                {
                    "memory_id": mem_id,
                    "content": doc,
                    "metadata": meta
                }
                for mem_id, doc, meta in zip(
                    results["ids"],
                    results["documents"],
                    results["metadatas"]
                )
            ]
        else:
            return self.memories.copy()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_memory(agent_name: str) -> AgentMemory:
    """Factory function to create agent memory"""
    return AgentMemory(agent_name)


def demo_memory():
    """Demo the memory system"""
    print("=== Agent Memory Demo ===\n")
    
    memory = AgentMemory("demo_agent")
    
    # Store some memories
    print("1. Storing memories...")
    memory.remember(
        "User prefers concise email responses with bullet points",
        MemoryType.PREFERENCE,
        {"user": "kowshik.naidu@contoso.com", "context": "email_drafting"}
    )
    
    memory.remember(
        "Successfully resolved Acme API issue by checking firewall rules",
        MemoryType.STRATEGY,
        {"project": "acme", "issue_type": "api"}
    )
    
    memory.remember(
        "User asked about P0 tasks at 9 AM",
        MemoryType.INTERACTION,
        {"user": "kowshik.naidu@contoso.com", "time": "morning"}
    )
    
    print(f"   Stored 3 memories. Total: {memory.count()}\n")
    
    # Recall memories
    print("2. Recalling relevant memories...")
    results = memory.recall("How does user like email responses?", n_results=2)
    
    for result in results:
        print(f"   📝 {result['content']}")
        print(f"      Relevance: {result['relevance']:.2f}\n")
    
    # Get recent memories
    print("3. Recent interactions...")
    recent = memory.get_recent(n=2)
    for mem in recent:
        print(f"   • {mem['content'][:50]}...")
    
    print("\n[OK] Demo complete!")


if __name__ == "__main__":
    demo_memory()
