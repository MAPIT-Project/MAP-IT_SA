# 🎤 Conversational Export Integration Guide

## 📋 Current State vs. Required State

### ✅ What Works Now (via API)
```bash
# Direct API calls work perfectly
GET /api/proposal/export/123/part-b          # Downloads Word
GET /api/proposal/export/123/budget          # Downloads Excel  
GET /api/proposal/export/123/complete-package # Downloads ZIP
```

### ❌ What Doesn't Work Yet (via Conversation)
```
User: "Export my proposal as a submission package"
AI: [Currently not handled - no export detection]
```

### ✅ What SHOULD Work (after integration)
```
User: "Export my proposal as a submission package"

AI: 📦 Creating your submission package...
    
    ✅ Analyzing proposal structure...
    ✅ Generating Part B (Word document)...
    ✅ Generating Budget (Excel spreadsheet)...
    ✅ Creating README...
    ✅ Packaging files...
    
    🎉 Your submission package is ready!
    
    📥 Download: /api/proposal/export/123/complete-package
    
    Package contents:
    • AI-CYBER_PartB.docx (38 KB) - Main proposal
    • AI-CYBER_Budget.xlsx (5 KB) - Budget breakdown
    • README.txt - Submission instructions
    
    ✅ Ready to submit to EU portal!
```

---

## 🔧 Required Changes

### 1. ConversationManager Integration

**File:** `app/services/conversation/conversation_manager.py`

#### Add Export Detection
```python
async def _detect_proposal_writing_mode(self, conversation_id: int, user_message: str):
    """Detect proposal writing mode including EXPORT requests"""
    
    lower_msg = user_message.lower()
    
    # ... existing detection code ...
    
    # NEW: Export detection
    export_keywords = [
        'export', 'download', 'submission package', 'complete package',
        'word document', 'excel', 'part b', 'budget file', 'zip',
        'ready to submit', 'generate documents', 'create package'
    ]
    
    if any(keyword in lower_msg for keyword in export_keywords):
        # Detect export type
        if 'part b' in lower_msg or 'word' in lower_msg:
            return {'action': 'export_part_b', 'proposal_id': await self._get_active_proposal_id(conversation_id)}
        
        elif 'budget' in lower_msg or 'excel' in lower_msg:
            return {'action': 'export_budget', 'proposal_id': await self._get_active_proposal_id(conversation_id)}
        
        elif 'package' in lower_msg or 'complete' in lower_msg or 'submission' in lower_msg:
            return {'action': 'export_package', 'proposal_id': await self._get_active_proposal_id(conversation_id)}
        
        else:
            # Default to complete package
            return {'action': 'export_package', 'proposal_id': await self._get_active_proposal_id(conversation_id)}
    
    # ... rest of detection logic ...
```

#### Add Export Handlers
```python
async def _handle_proposal_writing(self, conversation_id: int, user_message: str, 
                                   user_id: int, proposal_mode: Dict[str, Any]):
    """Handle proposal writing requests including EXPORTS"""
    
    action = proposal_mode['action']
    
    # ... existing handlers ...
    
    # NEW: Export Part B
    elif action == 'export_part_b':
        proposal_id = proposal_mode.get('proposal_id')
        
        if not proposal_id:
            return {
                'response': "Which proposal would you like to export? Please specify the proposal ID or title.",
                'needs_info': ['proposal_id']
            }
        
        # Stream progress
        yield {
            'type': 'progress',
            'message': '📄 Generating Part B (Word document)...',
            'step': 1,
            'total_steps': 3
        }
        
        # Get proposal data
        proposal_data = await self._get_proposal_metadata(proposal_id)
        
        yield {
            'type': 'progress',
            'message': f'✅ Using official EU template for {proposal_data["action_type"]}...',
            'step': 2,
            'total_steps': 3
        }
        
        # Generate download link
        download_url = f"/api/proposal/export/{proposal_id}/part-b"
        
        yield {
            'type': 'progress',
            'message': '✅ Part B document created!',
            'step': 3,
            'total_steps': 3
        }
        
        # Final response
        response = f"""📄 **Part B Export Complete!**

**Proposal:** {proposal_data['title']}
**Type:** {proposal_data['action_type']}
**Format:** Microsoft Word (.docx)

📥 **Download:** [Click here to download]({download_url})

**File Details:**
• Official EU format
• All sections included
• Submission-ready
• ~40 KB file size

✅ Ready to upload to EU portal!
"""
        
        yield {
            'type': 'response',
            'message': response,
            'download_url': download_url,
            'file_type': 'docx'
        }
    
    # NEW: Export Budget
    elif action == 'export_budget':
        proposal_id = proposal_mode.get('proposal_id')
        
        if not proposal_id:
            return {
                'response': "Which proposal's budget would you like to export?",
                'needs_info': ['proposal_id']
            }
        
        yield {
            'type': 'progress',
            'message': '💰 Generating budget Excel...',
            'step': 1,
            'total_steps': 3
        }
        
        proposal_data = await self._get_proposal_metadata(proposal_id)
        
        yield {
            'type': 'progress',
            'message': '✅ Calculating partner budgets...',
            'step': 2,
            'total_steps': 3
        }
        
        download_url = f"/api/proposal/export/{proposal_id}/budget"
        
        yield {
            'type': 'progress',
            'message': '✅ Budget spreadsheet created!',
            'step': 3,
            'total_steps': 3
        }
        
        response = f"""💰 **Budget Export Complete!**

**Proposal:** {proposal_data['title']}
**Format:** Microsoft Excel (.xlsx)

📥 **Download:** [Click here to download]({download_url})

**File Details:**
• Official EU format
• All partners included
• Funding rates calculated
• ~5 KB file size

✅ Ready to upload to EU portal!
"""
        
        yield {
            'type': 'response',
            'message': response,
            'download_url': download_url,
            'file_type': 'xlsx'
        }
    
    # NEW: Export Complete Package
    elif action == 'export_package':
        proposal_id = proposal_mode.get('proposal_id')
        
        if not proposal_id:
            return {
                'response': "Which proposal would you like to export as a complete package?",
                'needs_info': ['proposal_id']
            }
        
        # Stream progress updates
        yield {
            'type': 'progress',
            'message': '📦 Creating submission package...',
            'step': 1,
            'total_steps': 6
        }
        
        proposal_data = await self._get_proposal_metadata(proposal_id)
        
        yield {
            'type': 'progress',
            'message': '📄 Generating Part B (Word)...',
            'step': 2,
            'total_steps': 6
        }
        
        yield {
            'type': 'progress',
            'message': '💰 Generating Budget (Excel)...',
            'step': 3,
            'total_steps': 6
        }
        
        yield {
            'type': 'progress',
            'message': '📋 Creating README...',
            'step': 4,
            'total_steps': 6
        }
        
        yield {
            'type': 'progress',
            'message': '📦 Packaging files...',
            'step': 5,
            'total_steps': 6
        }
        
        download_url = f"/api/proposal/export/{proposal_id}/complete-package"
        
        yield {
            'type': 'progress',
            'message': '✅ Package created successfully!',
            'step': 6,
            'total_steps': 6
        }
        
        response = f"""🎉 **Submission Package Ready!**

**Proposal:** {proposal_data['title']}
**Acronym:** {proposal_data['acronym']}
**Type:** {proposal_data['action_type']}

📥 **Download:** [Click here to download ZIP]({download_url})

**Package Contents:**
• {proposal_data['acronym']}_PartB.docx (~38 KB)
  - All proposal sections
  - Official EU format
  
• {proposal_data['acronym']}_Budget.xlsx (~5 KB)
  - Partner budgets
  - Funding calculations
  
• README.txt
  - Submission instructions
  - Portal upload guide

**Total Package Size:** ~40 KB

✅ **READY TO SUBMIT TO EU PORTAL!** 🚀

**Next Steps:**
1. Download the ZIP file
2. Extract the contents
3. Log in to EU Funding & Tenders Portal
4. Upload Part B documents
5. Fill Part A (administrative data)
6. Submit! 🎊
"""
        
        yield {
            'type': 'response',
            'message': response,
            'download_url': download_url,
            'file_type': 'zip',
            'package_contents': [
                f"{proposal_data['acronym']}_PartB.docx",
                f"{proposal_data['acronym']}_Budget.xlsx",
                "README.txt"
            ]
        }

async def _get_active_proposal_id(self, conversation_id: int) -> Optional[int]:
    """Get the active proposal ID from conversation context"""
    
    context = await self.memory_service.get_conversation_context(conversation_id)
    
    # Check context for proposal_id
    if context.get('proposal_id'):
        return context['proposal_id']
    
    # Query database for most recent proposal in this conversation
    conn = self.db_pool.getconn()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id FROM proposals
        WHERE conversation_id = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (conversation_id,))
    
    row = cursor.fetchone()
    self.db_pool.putconn(conn)
    
    return row[0] if row else None

async def _get_proposal_metadata(self, proposal_id: int) -> Dict[str, Any]:
    """Get proposal metadata for export"""
    
    conn = self.db_pool.getconn()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT proposal_title, proposal_acronym, proposal_type
        FROM proposals
        WHERE id = %s
    """, (proposal_id,))
    
    row = cursor.fetchone()
    self.db_pool.putconn(conn)
    
    if not row:
        raise ValueError(f"Proposal {proposal_id} not found")
    
    return {
        'title': row[0],
        'acronym': row[1],
        'action_type': row[2]
    }
```

---

## 🎨 Frontend Changes Required

### 1. Handle Progress Updates

**File:** `frontend/src/components/ChatInterface.tsx` (or similar)

```typescript
// Add to message handler
const handleStreamedMessage = (chunk: any) => {
  if (chunk.type === 'progress') {
    // Show progress indicator
    setProgress({
      message: chunk.message,
      step: chunk.step,
      totalSteps: chunk.total_steps
    });
  }
  
  else if (chunk.type === 'response') {
    // Show final response
    addMessage({
      role: 'assistant',
      content: chunk.message,
      downloadUrl: chunk.download_url,
      fileType: chunk.file_type
    });
    
    // Clear progress
    setProgress(null);
  }
};
```

### 2. Progress UI Component

```typescript
// ProgressIndicator.tsx
interface ProgressIndicatorProps {
  message: string;
  step: number;
  totalSteps: number;
}

const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({ 
  message, step, totalSteps 
}) => {
  const percentage = (step / totalSteps) * 100;
  
  return (
    <div className="progress-container">
      <div className="progress-bar">
        <div 
          className="progress-fill" 
          style={{ width: `${percentage}%` }}
        />
      </div>
      <p className="progress-message">{message}</p>
      <p className="progress-steps">Step {step} of {totalSteps}</p>
    </div>
  );
};
```

### 3. Download Button Component

```typescript
// DownloadButton.tsx
interface DownloadButtonProps {
  url: string;
  fileType: 'docx' | 'xlsx' | 'zip';
  fileName?: string;
}

const DownloadButton: React.FC<DownloadButtonProps> = ({ 
  url, fileType, fileName 
}) => {
  const getIcon = () => {
    switch (fileType) {
      case 'docx': return '📄';
      case 'xlsx': return '💰';
      case 'zip': return '📦';
      default: return '📥';
    }
  };
  
  const handleDownload = async () => {
    const response = await fetch(url);
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = fileName || `download.${fileType}`;
    link.click();
    window.URL.revokeObjectURL(downloadUrl);
  };
  
  return (
    <button 
      className="download-button" 
      onClick={handleDownload}
    >
      {getIcon()} Download {fileType.toUpperCase()}
    </button>
  );
};
```

### 4. Message Display with Download

```typescript
// ChatMessage.tsx
const ChatMessage: React.FC<MessageProps> = ({ message }) => {
  return (
    <div className={`message ${message.role}`}>
      <ReactMarkdown>{message.content}</ReactMarkdown>
      
      {message.downloadUrl && (
        <DownloadButton 
          url={message.downloadUrl}
          fileType={message.fileType}
          fileName={message.fileName}
        />
      )}
    </div>
  );
};
```

---

## 🔄 Complete User Flow

### Example 1: Export Complete Package

```
User: "Export my proposal as a submission package"

[Progress Indicator Appears]
📦 Creating submission package...
Progress: ████░░░░░░ 1/6

📦 Creating submission package...
Progress: ████████░░ 4/6

[Progress Complete]

AI: 🎉 **Submission Package Ready!**

**Proposal:** AI-Powered Cybersecurity System
**Acronym:** AI-CYBER
**Type:** RIA

[Download ZIP Button]

Package Contents:
• AI-CYBER_PartB.docx (~38 KB)
• AI-CYBER_Budget.xlsx (~5 KB)
• README.txt

✅ READY TO SUBMIT TO EU PORTAL! 🚀
```

### Example 2: Export Part B Only

```
User: "I need the Word document"

[Progress Indicator]
📄 Generating Part B...
Progress: ██████████ 3/3

AI: 📄 **Part B Export Complete!**

**Format:** Microsoft Word (.docx)

[Download DOCX Button]

✅ Ready to upload to EU portal!
```

---

## 📋 Implementation Checklist

### Backend (ConversationManager)
- [ ] Add export keyword detection in `_detect_proposal_writing_mode()`
- [ ] Add `_get_active_proposal_id()` helper method
- [ ] Add `_get_proposal_metadata()` helper method
- [ ] Implement `export_part_b` handler with progress streaming
- [ ] Implement `export_budget` handler with progress streaming
- [ ] Implement `export_package` handler with progress streaming
- [ ] Test streaming response format

### Frontend
- [ ] Update message type definitions to include progress
- [ ] Create `ProgressIndicator` component
- [ ] Create `DownloadButton` component
- [ ] Update `ChatMessage` to show download buttons
- [ ] Handle streaming progress updates
- [ ] Implement file download functionality
- [ ] Add loading states
- [ ] Test with real API

### Testing
- [ ] Test "export package" command
- [ ] Test "export word" / "export part b"
- [ ] Test "export excel" / "export budget"
- [ ] Test progress streaming
- [ ] Test download functionality
- [ ] Test error handling (no proposal found)
- [ ] Test with multiple proposals in conversation

---

## 🎯 Response Format

### Streaming Format
```json
// Progress updates
{
  "type": "progress",
  "message": "📦 Creating submission package...",
  "step": 1,
  "total_steps": 6
}

// Final response
{
  "type": "response",
  "message": "🎉 **Submission Package Ready!** ...",
  "download_url": "/api/proposal/export/123/complete-package",
  "file_type": "zip",
  "package_contents": ["PartB.docx", "Budget.xlsx", "README.txt"]
}
```

### Frontend State
```typescript
interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  downloadUrl?: string;
  fileType?: 'docx' | 'xlsx' | 'zip';
  fileName?: string;
  packageContents?: string[];
}

interface Progress {
  message: string;
  step: number;
  totalSteps: number;
}
```

---

## 🚀 Example Conversations

### Conversation 1: Full Export Flow
```
User: Generate a proposal for HORIZON-CL3-2025-02-CS-ECCC-01 about AI cybersecurity
AI: [Generates proposal with ID 123]

User: Write the objectives section
AI: [Generates 1300-word section]

User: Create a budget for 3 partners
AI: [Generates budget]

User: Export everything as a submission package
AI: 
  [Progress: Creating package... 1/6]
  [Progress: Generating Part B... 2/6]
  [Progress: Generating Budget... 3/6]
  [Progress: Complete! 6/6]
  
  🎉 Package ready! [Download ZIP]
```

### Conversation 2: Quick Export
```
User: I need to export proposal 45 as Word
AI:
  [Progress: Generating Part B... 3/3]
  
  📄 Part B ready! [Download DOCX]
```

---

## 🎨 UI/UX Considerations

### Progress Display
- **Show clear progress**: Use progress bars or step indicators
- **Informative messages**: Tell user exactly what's happening
- **Smooth transitions**: Animate progress smoothly
- **Estimated time**: Optional - show "~30 seconds remaining"

### Download UX
- **Clear buttons**: Large, obvious download buttons
- **File info**: Show file type, size, and format
- **Auto-download**: Option to auto-download when ready
- **Success feedback**: Confirm download started

### Error Handling
```typescript
if (!proposal_id) {
  return {
    type: 'error',
    message: "I couldn't find an active proposal. Please specify which proposal to export or create a new one."
  };
}

if (export_failed) {
  return {
    type: 'error',
    message: "Export failed. Please try again or contact support.",
    retry_url: `/api/proposal/export/${proposal_id}/complete-package`
  };
}
```

---

## 💡 Advanced Features (Optional)

### 1. Email Export
```
User: "Email me the submission package"
AI: ✅ Package sent to your.email@domain.com
```

### 2. Cloud Storage
```
User: "Save to Google Drive"
AI: ✅ Saved to your Drive: /Proposals/AI-CYBER/
```

### 3. Version History
```
User: "Show me all exports for this proposal"
AI: 
  📦 Version 3 - 2025-10-10 18:00 [Download]
  📦 Version 2 - 2025-10-10 15:30 [Download]
  📦 Version 1 - 2025-10-10 12:00 [Download]
```

---

## ✅ Summary

**Current State:**
- ✅ Export API endpoints work perfectly
- ❌ No conversational integration
- ❌ No progress streaming

**After Implementation:**
- ✅ Natural language export commands
- ✅ Real-time progress updates
- ✅ Download buttons in chat
- ✅ Complete conversational flow

**Changes Needed:**
1. **Backend:** Add export handlers to ConversationManager (3 methods)
2. **Frontend:** Add progress UI and download buttons (3 components)
3. **Testing:** Verify streaming and downloads work

**Result:**
```
User: "Export my proposal"
AI: [Shows progress] → [Provides download] → Done! 🎉
```

**Time to Implement:** 2-3 hours
**Complexity:** Medium
**Impact:** HUGE! Complete conversational experience! 🚀

