# Frontend Citation Integration Guide

## 🎯 Making Citations Clickable

The API now returns **structured citation data** that you can use to create clickable, expandable citations in your frontend.

---

## 📊 **API Response Format**

### **Non-Streaming Endpoint (`/message`):**

#### **Before (Old - Just Strings):**
```json
{
  "response": "Switzerland is eligible [1]. The budget is €12M-€14M [2].",
  "citations": [
    "Call Metadata for HORIZON-CL3-2025-02-CS-ECCC-01 (EU Portal API)",
    "Horizon Europe Programme Guide - Budget Section"
  ]
}
```

#### **After (New - Structured Objects):**
```json
{
  "response": "Switzerland is eligible [1]. The budget is €12M-€14M [2].",
  "citations": [
    {
      "number": 1,
      "text": "Call Metadata for HORIZON-CL3-2025-02-CS-ECCC-01 (EU Portal API)",
      "chunk_id": "metadata_HORIZON-CL3-2025-02-CS-ECCC-01",
      "content_snippet": "**CALL METADATA (Official API Data)**\n\nTitle: Generative AI for Cybersecurity applications\n\nELIGIBILITY:\n- Eligible Countries: Member States and Associated Countries...",
      "metadata": {
        "source": "call_metadata_api",
        "call_id": "HORIZON-CL3-2025-02-CS-ECCC-01",
        "is_structured": true,
        "priority": "high"
      },
      "source_type": "call_metadata_api"
    },
    {
      "number": 2,
      "text": "Horizon Europe Programme Guide - Budget Section",
      "chunk_id": "chunk_12345",
      "content_snippet": "The budget for Research and Innovation Actions (RIA) typically ranges from €3M to €15M depending on the call...",
      "metadata": {
        "source": "call_documents",
        "call_id": "HORIZON-CL3-2025-02-CS-ECCC-01",
        "document_type": "programme_guide",
        "relevance_score": 0.95
      },
      "source_type": "call_documents"
    }
  ]
}
```

---

### **Streaming Endpoint (`/message/stream`):**

The streaming endpoint sends **Server-Sent Events (SSE)**. Citations are included in the final `complete` event:

```typescript
// Event types you'll receive:
{
  type: 'status',      // Initial status
  message: string
}

{
  type: 'token',       // Text chunks as they're generated
  content: string
}

{
  type: 'complete',    // Final event with ALL metadata
  citations: Citation[],  // ✨ Structured citations here!
  confidence: number,
  grounded: boolean,
  processing_time: number,
  // ... other metadata
}
```

**Example:**
```json
data: {"type": "token", "content": "Yes, you can apply from Switzerland"}
data: {"type": "token", "content": " for HORIZON-CL3-2025-02-CS-ECCC-01."}
data: {"type": "token", "content": " [1] [2]"}
data: {
  "type": "complete",
  "citations": [
    {
      "number": 1,
      "text": "Call Metadata (EU Portal API)",
      "chunk_id": "metadata_HORIZON-CL3-2025-02-CS-ECCC-01",
      "content_snippet": "Eligible Countries: Member States...",
      "source_type": "call_metadata_api"
    }
  ],
  "confidence": 0.95,
  "grounded": true
}
```

---

## 🎨 **Frontend Implementation**

### **React/TypeScript Example:**

```typescript
interface Citation {
  number: number;
  text: string;
  chunk_id: string;
  content_snippet: string;
  metadata: {
    source: string;
    call_id?: string;
    document_type?: string;
    relevance_score?: number;
    is_structured?: boolean;
    priority?: string;
  };
  source_type: string;
}

interface APIResponse {
  response: string;
  citations: Citation[];
  confidence: number;
  grounded: boolean;
}

// Component
function CitationPopover({ citation }: { citation: Citation }) {
  const [isOpen, setIsOpen] = useState(false);
  
  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <button className="citation-link">
          [{citation.number}]
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-96">
        <div className="space-y-3">
          <div>
            <h4 className="font-semibold text-sm mb-1">Source</h4>
            <p className="text-sm text-gray-700">{citation.text}</p>
          </div>
          
          <div>
            <h4 className="font-semibold text-sm mb-1">Content Preview</h4>
            <p className="text-xs text-gray-600 bg-gray-50 p-2 rounded max-h-32 overflow-y-auto">
              {citation.content_snippet}
            </p>
          </div>
          
          {citation.source_type === 'call_metadata_api' && (
            <div className="bg-blue-50 p-2 rounded">
              <p className="text-xs text-blue-800">
                ✓ Official API Data - Authoritative Source
              </p>
            </div>
          )}
          
          {citation.metadata.document_type && (
            <div>
              <span className="text-xs bg-gray-200 px-2 py-1 rounded">
                {citation.metadata.document_type}
              </span>
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}

// Render response with inline citations
function ResponseWithCitations({ data }: { data: APIResponse }) {
  const renderTextWithCitations = (text: string, citations: Citation[]) => {
    // Split text by citation markers [1], [2], etc.
    const parts = text.split(/(\[\d+\])/g);
    
    return parts.map((part, index) => {
      const citationMatch = part.match(/\[(\d+)\]/);
      
      if (citationMatch) {
        const citationNumber = parseInt(citationMatch[1]);
        const citation = citations.find(c => c.number === citationNumber);
        
        if (citation) {
          return <CitationPopover key={index} citation={citation} />;
        }
      }
      
      return <span key={index}>{part}</span>;
    });
  };
  
  return (
    <div>
      <div className="prose">
        {renderTextWithCitations(data.response, data.citations)}
      </div>
      
      {/* Optional: Citation list at the bottom */}
      <div className="mt-6 border-t pt-4">
        <h3 className="text-sm font-semibold mb-2">Sources</h3>
        <ol className="text-sm space-y-1">
          {data.citations.map(citation => (
            <li key={citation.number} className="text-gray-600">
              {citation.text}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
```

---

## 🎨 **Vue.js Example:**

```vue
<template>
  <div class="response-container">
    <!-- Render text with inline citations -->
    <div class="prose" v-html="formattedResponse"></div>
    
    <!-- Citation popovers -->
    <div v-for="citation in citations" :key="citation.number">
      <el-popover
        :ref="`popover-${citation.number}`"
        placement="top"
        width="400"
        trigger="hover"
      >
        <template #reference>
          <span class="citation-marker">[{{ citation.number }}]</span>
        </template>
        
        <div>
          <h4 class="font-bold text-sm mb-2">{{ citation.text }}</h4>
          <p class="text-xs bg-gray-100 p-2 rounded">
            {{ citation.content_snippet }}
          </p>
          <div v-if="citation.source_type === 'call_metadata_api'" 
               class="mt-2 text-blue-600 text-xs">
            ✓ Official API Data
          </div>
        </div>
      </el-popover>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  response: string;
  citations: Citation[];
}

const props = defineProps<Props>();

const formattedResponse = computed(() => {
  let html = props.response;
  
  // Replace [1], [2] etc. with clickable elements
  props.citations.forEach(citation => {
    const regex = new RegExp(`\\[${citation.number}\\]`, 'g');
    html = html.replace(
      regex,
      `<span class="citation-link" data-citation="${citation.number}">[${citation.number}]</span>`
    );
  });
  
  return html;
});
</script>

<style scoped>
.citation-link {
  color: #3b82f6;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.citation-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}
</style>
```

---

## 🎨 **Simple HTML/JS Example:**

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    .citation {
      color: #2563eb;
      cursor: pointer;
      font-weight: 600;
      position: relative;
    }
    
    .citation:hover {
      text-decoration: underline;
    }
    
    .citation-tooltip {
      display: none;
      position: absolute;
      bottom: 100%;
      left: 0;
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 12px;
      width: 350px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      z-index: 1000;
    }
    
    .citation:hover .citation-tooltip {
      display: block;
    }
    
    .tooltip-title {
      font-weight: bold;
      margin-bottom: 8px;
      font-size: 14px;
    }
    
    .tooltip-content {
      font-size: 12px;
      color: #6b7280;
      background: #f9fafb;
      padding: 8px;
      border-radius: 4px;
      max-height: 120px;
      overflow-y: auto;
    }
  </style>
</head>
<body>
  <div id="response"></div>
  
  <script>
    function renderCitations(responseText, citations) {
      const container = document.getElementById('response');
      
      // Split by citation markers
      const parts = responseText.split(/(\[\d+\])/g);
      
      parts.forEach(part => {
        const match = part.match(/\[(\d+)\]/);
        
        if (match) {
          const citationNum = parseInt(match[1]);
          const citation = citations.find(c => c.number === citationNum);
          
          if (citation) {
            const citationEl = document.createElement('span');
            citationEl.className = 'citation';
            citationEl.textContent = `[${citationNum}]`;
            
            const tooltip = document.createElement('div');
            tooltip.className = 'citation-tooltip';
            tooltip.innerHTML = `
              <div class="tooltip-title">${citation.text}</div>
              <div class="tooltip-content">${citation.content_snippet}</div>
            `;
            
            citationEl.appendChild(tooltip);
            container.appendChild(citationEl);
          }
        } else {
          container.appendChild(document.createTextNode(part));
        }
      });
    }
    
    // Example usage:
    const apiResponse = {
      response: "Switzerland is eligible [1]. Budget: €12M-€14M [2].",
      citations: [
        {
          number: 1,
          text: "Call Metadata (EU Portal API)",
          content_snippet: "Eligible Countries: Member States and Associated Countries..."
        },
        {
          number: 2,
          text: "Horizon Europe Programme Guide",
          content_snippet: "The budget for RIA actions ranges from €3M to €15M..."
        }
      ]
    };
    
    renderCitations(apiResponse.response, apiResponse.citations);
  </script>
</body>
</html>
```

---

---

## 🌊 **Streaming Response Handler**

### **React Example with SSE:**

```typescript
function useStreamingChat() {
  const [message, setMessage] = useState('');
  const [citations, setCitations] = useState<Citation[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);

  const sendMessage = async (userMessage: string) => {
    setMessage('');
    setCitations([]);
    setIsStreaming(true);

    const response = await fetch('/api/v2/conversation/123/message/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userMessage })
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader!.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));

          if (data.type === 'token') {
            // Accumulate text tokens
            setMessage(prev => prev + data.content);
          } 
          else if (data.type === 'complete') {
            // ✨ Get citations from the complete event
            setCitations(data.citations || []);
            setIsStreaming(false);
          }
        }
      }
    }
  };

  return { message, citations, isStreaming, sendMessage };
}

// Usage:
function ChatComponent() {
  const { message, citations, isStreaming, sendMessage } = useStreamingChat();

  return (
    <div>
      {/* Render streaming message */}
      <div className="prose">
        {renderTextWithCitations(message, citations)}
      </div>

      {/* Show citations when complete */}
      {!isStreaming && citations.length > 0 && (
        <div className="mt-4">
          <h4 className="font-semibold">Sources</h4>
          {citations.map(citation => (
            <CitationCard key={citation.number} citation={citation} />
          ))}
        </div>
      )}
    </div>
  );
}
```

### **Vue 3 Composition API:**

```vue
<script setup lang="ts">
import { ref } from 'vue';

const message = ref('');
const citations = ref<Citation[]>([]);
const isStreaming = ref(false);

async function sendMessage(userMessage: string) {
  message.value = '';
  citations.value = [];
  isStreaming.value = true;

  const response = await fetch('/api/v2/conversation/123/message/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: userMessage })
  });

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));

        if (data.type === 'token') {
          message.value += data.content;
        } 
        else if (data.type === 'complete') {
          citations.value = data.citations || [];
          isStreaming.value = false;
        }
      }
    }
  }
}
</script>

<template>
  <div>
    <div v-html="message"></div>
    
    <!-- Citations appear when streaming completes -->
    <div v-if="!isStreaming && citations.length > 0" class="citations">
      <h4>Sources</h4>
      <CitationCard 
        v-for="citation in citations" 
        :key="citation.number"
        :citation="citation" 
      />
    </div>
  </div>
</template>
```

---

## 📱 **Mobile-Friendly Implementation**

For mobile, use a modal/drawer instead of popover:

```typescript
function CitationModal({ citation, isOpen, onClose }: CitationModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Source [{citation.number}]</DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          <div>
            <p className="text-sm font-medium">{citation.text}</p>
          </div>
          
          <div>
            <h4 className="text-sm font-semibold mb-2">Content</h4>
            <p className="text-sm bg-gray-50 p-3 rounded">
              {citation.content_snippet}
            </p>
          </div>
          
          {citation.metadata.document_type && (
            <div className="flex gap-2">
              <Badge variant="secondary">
                {citation.metadata.document_type}
              </Badge>
              {citation.source_type === 'call_metadata_api' && (
                <Badge variant="default">Official API</Badge>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

---

## 🎨 **Styling Suggestions**

```css
/* Citation link in text */
.citation-link {
  color: #2563eb;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  padding: 0 2px;
  border-radius: 2px;
}

.citation-link:hover {
  background: #dbeafe;
  text-decoration: underline;
}

/* Different styles based on source type */
.citation-link[data-source="call_metadata_api"] {
  color: #059669; /* Green for official API data */
}

.citation-link[data-source="call_documents"] {
  color: #2563eb; /* Blue for documents */
}

.citation-link[data-source="general"] {
  color: #7c3aed; /* Purple for general docs */
}
```

---

## ✅ **Benefits**

1. **Transparency** - Users can see exactly where information came from
2. **Trust** - Official API sources are clearly marked
3. **Context** - Content preview shows what the source says
4. **Mobile-Friendly** - Works on all devices
5. **Professional** - Looks like academic citations

---

## 🚀 **Ready to Use!**

Your API is now returning structured citations. Just implement one of the frontend examples above and users can click on [1], [2] etc. to see the sources!


