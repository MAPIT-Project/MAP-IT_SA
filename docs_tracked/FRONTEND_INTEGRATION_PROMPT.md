# Frontend Integration Prompt: MAP-IT Enhanced Features

## Overview

This document provides detailed specifications for integrating the new backend features into the MAP-IT frontend. The backend now supports 20 tools (up from 18), performance optimizations, user feedback collection, and enhanced response formatting with publications/deliverables.

---

## 1. Existing Conversation API (V3)

The frontend should already be using these endpoints:

```
POST /api/v3/conversation/{conversation_id}/message/stream  - Streaming responses (SSE)
POST /api/v3/conversation/{conversation_id}/message         - Non-streaming responses
GET  /api/v3/conversation/{conversation_id}/context         - Get conversation history
DELETE /api/v3/conversation/{conversation_id}/context       - Clear conversation
GET  /api/v3/conversation/health                            - Health check
```

### SSE Event Types

Events are now streamed **in real-time** as the agent thinks and executes tools. This means the frontend gets immediate updates during processing, not after.

```typescript
type SSEEvent =
  | { type: 'status'; stage: string; message: string }
  | { type: 'conversation_name'; name: string; conversation_id: number }  // First message only
  | { type: 'agent_thinking'; stage: 'reasoning'; iteration: number; thought: string; action: string }  // REAL-TIME
  | { type: 'tool_call'; stage: 'executing_tool'; tool_name: string; parameters: Record<string, any>; reasoning: string; iteration: number }  // REAL-TIME
  | { type: 'tool_result'; stage: 'tool_complete'; tool_name: string; success: boolean; result_count: number; result_summary: string; execution_time_ms: number; iteration: number }  // REAL-TIME
  | { type: 'token'; content: string }
  | { type: 'complete'; metadata: ResponseMetadata }
  | { type: 'error'; message: string; code?: string }
```

### Real-Time Agent Events

Agent thinking and tool execution events are now streamed **as they happen**, not after processing completes. This gives users immediate feedback:

```typescript
// Example event sequence (real-time):
// 1. Agent starts thinking (sent immediately)
{ "type": "agent_thinking", "stage": "reasoning", "iteration": 1, "thought": "User is asking about hydrogen funding calls. I should search for open funding opportunities.", "action": "call_tools" }

// 2. Tool call announced before execution
{ "type": "tool_call", "stage": "executing_tool", "tool_name": "search_funding_calls", "parameters": {"keywords": "hydrogen", "status": "open"}, "reasoning": "Search for open hydrogen funding calls", "iteration": 1 }

// 3. Tool result after execution completes
{ "type": "tool_result", "stage": "tool_complete", "tool_name": "search_funding_calls", "success": true, "result_count": 15, "result_summary": "Found 15 funding calls...", "execution_time_ms": 245, "iteration": 1 }

// 4. Agent may think again if more info needed
{ "type": "agent_thinking", "stage": "reasoning", "iteration": 2, "thought": "Found good results, I can now provide the answer", "action": "conclude" }

// 5. Response tokens stream
{ "type": "token", "content": "I found **15 funding opportunities**..." }
```

### Frontend UX Recommendations

```typescript
function handleSSEEvent(event: SSEEvent) {
  switch (event.type) {
    case 'agent_thinking':
      // Show thinking indicator with the thought
      showThinkingBubble({
        iteration: event.iteration,
        thought: event.thought,
        action: event.action  // 'call_tools' or 'conclude'
      });
      break;

    case 'tool_call':
      // Show which tool is being called
      showToolExecuting({
        toolName: event.tool_name,
        parameters: event.parameters,
        reasoning: event.reasoning
      });
      break;

    case 'tool_result':
      // Show result count and success
      showToolComplete({
        toolName: event.tool_name,
        success: event.success,
        resultCount: event.result_count,
        executionTime: event.execution_time_ms
      });
      break;

    case 'token':
      // Append to response (hide thinking UI)
      hideThinkingUI();
      appendToResponse(event.content);
      break;
    // ... other handlers
  }
}
```

### NEW: Automatic Conversation Naming

When the user sends their **first message** in a conversation, the backend automatically generates a descriptive name based on the message content. This is streamed back as a `conversation_name` event.

**Event structure:**
```json
{
  "type": "conversation_name",
  "name": "Hydrogen Funding Calls",
  "conversation_id": 12345
}
```

**Frontend handling:**
```typescript
// In your SSE event handler
function handleSSEEvent(event: SSEEvent) {
  switch (event.type) {
    case 'conversation_name':
      // Update the conversation title in the sidebar/header
      updateConversationName(event.conversation_id, event.name);
      // Also update in your conversation list/store
      conversationStore.setName(event.conversation_id, event.name);
      break;
    // ... other event handlers
  }
}

// Update sidebar conversation list
function updateConversationName(conversationId: number, name: string) {
  // Find the conversation in sidebar and update its display name
  const conversationElement = document.querySelector(`[data-conversation-id="${conversationId}"]`);
  if (conversationElement) {
    conversationElement.querySelector('.conversation-name').textContent = name;
  }
}
```

**Example conversation names generated:**
| User's First Message | Generated Name |
|---------------------|----------------|
| "What hydrogen funding calls are open?" | "Hydrogen Funding Calls" |
| "Can universities from Switzerland participate?" | "Swiss Eligibility" |
| "Compare ERC and EIC programmes" | "ERC vs EIC Comparison" |
| "Help me write a proposal for AI research" | "AI Research Proposal" |
| "What are the success rates for RIA grants?" | "RIA Success Rates" |
| "Find projects about renewable energy" | "Renewable Energy Projects" |

**Important notes:**
1. The `conversation_name` event is only sent for the **first message** in a conversation
2. The name is also persisted in the database (`conversation.name` column)
3. If name generation fails, no event is sent (graceful degradation)
4. Names are 2-5 words, title-cased, and descriptive

---

## 2. NEW: User Feedback System

### 2.1 Feedback API Endpoints

```
POST   /api/feedback                      - Submit feedback
GET    /api/feedback/summary              - Get feedback metrics
GET    /api/feedback/conversation/{id}    - Get feedback for conversation
GET    /api/feedback/suggestions          - Get improvement suggestions
GET    /api/feedback/health               - Health check
```

### 2.2 Submit Feedback Request

```typescript
interface FeedbackSubmission {
  conversation_id: string;      // Required - the conversation ID
  message_id?: string;          // Optional - specific message being rated
  rating: 1 | 2 | 3 | 4 | 5;   // Required - 1-5 star rating
  feedback_type: 'helpful' | 'not_helpful' | 'incorrect' | 'incomplete' | 'other';
  feedback_text?: string;       // Optional - free-form comments
  query_text?: string;          // Optional - the user's original query
  response_text?: string;       // Optional - the AI response (truncated)
  tools_used?: string[];        // Optional - which tools were used
  query_type?: string;          // Optional - 'faq', 'search_calls', 'search_projects', etc.
  response_time_ms?: number;    // Optional - how long the response took
}

// Example request
POST /api/feedback
{
  "conversation_id": "conv-abc123",
  "message_id": "msg-xyz789",
  "rating": 4,
  "feedback_type": "helpful",
  "feedback_text": "Great response, but could include more budget details",
  "tools_used": ["search_funding_calls", "get_call_details"]
}

// Response
{
  "success": true,
  "feedback_id": 42,
  "message": "Thank you for your feedback!"
}
```

### 2.3 UI Component: Feedback Widget

Add a feedback widget that appears after each AI response:

```tsx
interface FeedbackWidgetProps {
  conversationId: string;
  messageId: string;
  toolsUsed: string[];
  responseTimeMs: number;
  onFeedbackSubmitted?: (feedback: FeedbackSubmission) => void;
}

// Suggested UI elements:
// 1. Thumbs up/down quick feedback (maps to helpful/not_helpful)
// 2. Star rating (1-5) for detailed feedback
// 3. Optional text input for comments
// 4. Feedback type selector for negative feedback (incorrect/incomplete/other)

// Example component structure:
<FeedbackWidget>
  <QuickFeedback>
    <ThumbsUpButton onClick={() => submitFeedback({ rating: 5, feedback_type: 'helpful' })} />
    <ThumbsDownButton onClick={() => setShowDetailedFeedback(true)} />
  </QuickFeedback>

  {showDetailedFeedback && (
    <DetailedFeedback>
      <StarRating value={rating} onChange={setRating} />
      <FeedbackTypeSelect
        options={['not_helpful', 'incorrect', 'incomplete', 'other']}
        value={feedbackType}
        onChange={setFeedbackType}
      />
      <TextArea
        placeholder="Tell us more about your experience..."
        value={feedbackText}
        onChange={setFeedbackText}
      />
      <SubmitButton onClick={handleSubmit} />
    </DetailedFeedback>
  )}
</FeedbackWidget>
```

### 2.4 Placement Recommendations

1. **Inline with responses**: Show thumbs up/down after each AI response
2. **Expandable**: Click thumbs down to expand detailed feedback form
3. **Non-intrusive**: Don't block the conversation flow
4. **Dismissible**: User can skip feedback entirely
5. **Remember state**: Don't show feedback widget for already-rated messages

---

## 3. NEW: Enhanced Tool Display

### 3.1 New Tools Available (20 Total)

The agent now has 20 tools. Display tool usage during streaming:

```typescript
const TOOL_DISPLAY_CONFIG: Record<string, { icon: string; label: string; description: string }> = {
  // Statistics Tools
  'get_programme_statistics': { icon: '📊', label: 'Programme Stats', description: 'Getting success rates and funding data' },
  'get_country_statistics': { icon: '🌍', label: 'Country Stats', description: 'Getting participation statistics' },

  // Comparison Tools
  'compare_programmes': { icon: '⚖️', label: 'Compare', description: 'Comparing programmes side-by-side' },

  // Document Tools
  'search_documents': { icon: '📄', label: 'Documents', description: 'Searching EU documents' },

  // Call Tools
  'search_funding_calls': { icon: '📢', label: 'Funding Calls', description: 'Finding open funding opportunities' },
  'get_call_details': { icon: '🔍', label: 'Call Details', description: 'Getting detailed call information' },

  // Project Tools
  'search_projects': { icon: '🔬', label: 'Projects', description: 'Searching funded projects' },
  'get_project_details': { icon: '📋', label: 'Project Details', description: 'Getting project information' },
  'find_similar_projects': { icon: '🔗', label: 'Similar Projects', description: 'Finding related projects' },
  'find_semantically_similar_projects': { icon: '🧠', label: 'AI Similar', description: 'Finding semantically similar projects' },
  'find_organization_projects': { icon: '🏢', label: 'Org Projects', description: 'Finding organization\'s projects' },
  'get_collaboration_network': { icon: '🤝', label: 'Network', description: 'Mapping collaboration patterns' },
  'search_by_cluster': { icon: '🎯', label: 'Cluster Search', description: 'Searching by research cluster' },

  // Proposal Support Tools
  'get_budget_benchmark': { icon: '💰', label: 'Budget Benchmark', description: 'Getting budget statistics' },
  'get_consortium_patterns': { icon: '👥', label: 'Consortium', description: 'Analyzing consortium patterns' },
  'find_experienced_partners': { icon: '🎓', label: 'Partners', description: 'Finding experienced partners' },
  'get_similar_funded_projects': { icon: '✅', label: 'Funded Similar', description: 'Finding similar funded projects' },
  'analyze_call_history': { icon: '📈', label: 'History', description: 'Analyzing funding history' },

  // NEW: Proposal Planning Tools
  'calculate_budget': { icon: '🧮', label: 'Budget Calculator', description: 'Calculating budget breakdown' },
  'generate_timeline': { icon: '📅', label: 'Timeline', description: 'Generating project timeline' },
};
```

### 3.2 Tool Execution Display Component

Show tool execution in real-time during streaming:

```tsx
interface ToolExecutionProps {
  tool: string;
  args: Record<string, any>;
  status: 'executing' | 'completed' | 'failed';
  result?: Record<string, any>;
  executionTimeMs?: number;
}

// Example component
<ToolExecution tool="search_funding_calls" status="executing">
  <ToolIcon>{TOOL_DISPLAY_CONFIG['search_funding_calls'].icon}</ToolIcon>
  <ToolLabel>{TOOL_DISPLAY_CONFIG['search_funding_calls'].label}</ToolLabel>
  <ToolDescription>{TOOL_DISPLAY_CONFIG['search_funding_calls'].description}</ToolDescription>
  <Spinner /> {/* While executing */}
</ToolExecution>

// When completed
<ToolExecution tool="search_funding_calls" status="completed">
  <ToolIcon>📢</ToolIcon>
  <ToolLabel>Funding Calls</ToolLabel>
  <ResultSummary>Found 15 calls</ResultSummary>
  <ExecutionTime>250ms</ExecutionTime>
  <ExpandButton onClick={toggleDetails} /> {/* Optional: show raw results */}
</ToolExecution>
```

### 3.3 Agent Thinking Display

Show the agent's reasoning process:

```tsx
interface AgentThinkingProps {
  content: string;
  iteration: number;
  maxIterations: number;
}

// Example: Show as a subtle, expandable section
<AgentThinking>
  <ThinkingHeader>
    <BrainIcon />
    <span>Agent reasoning (Step {iteration}/{maxIterations})</span>
    <ExpandToggle />
  </ThinkingHeader>
  {expanded && (
    <ThinkingContent>
      {content}
    </ThinkingContent>
  )}
</AgentThinking>
```

---

## 4. NEW: Budget Calculator Results Display

When the `calculate_budget` tool is used, display the results in a structured format:

### 4.1 Budget Response Structure

```typescript
interface BudgetCalculation {
  success: boolean;
  tool_name: 'calculate_budget';
  calculated_budget: {
    total_cost: number;
    eu_contribution: number;
    funding_rate: string;  // e.g., "100%"
  };
  breakdown: {
    personnel: { amount: number; percentage: number; description: string; person_months: number };
    equipment: { amount: number; percentage: number; description: string };
    travel: { amount: number; percentage: number; description: string };
    subcontracting: { amount: number; percentage: number; description: string };
    other_direct: { amount: number; percentage: number; description: string };
    indirect: { amount: number; percentage: number; description: string };
  };
  per_partner: {
    average: number;
    coordinator_typical: number;
    partner_typical: number;
    pms_per_partner: number;
  };
  effort_summary: {
    total_person_months: number;
    person_months_per_partner: number;
    avg_pm_cost_used: number;
    pm_per_month: number;
  };
  benchmarks: {
    typical_range: string;  // e.g., "€2.6M - €9.2M"
    median: string;         // e.g., "€4.9M"
    your_budget_vs_median: 'within range' | 'below typical' | 'above typical';
  };
  recommendations: string[];
}
```

### 4.2 Budget Display Component

```tsx
<BudgetCalculationResult>
  {/* Summary Card */}
  <BudgetSummary>
    <TotalBudget>€{formatNumber(budget.calculated_budget.total_cost)}</TotalBudget>
    <EUContribution>
      EU Contribution: €{formatNumber(budget.calculated_budget.eu_contribution)}
      <FundingRate>{budget.calculated_budget.funding_rate}</FundingRate>
    </EUContribution>
    <BenchmarkIndicator status={budget.benchmarks.your_budget_vs_median}>
      {budget.benchmarks.your_budget_vs_median === 'within range' ? '✅' : '⚠️'}
      {budget.benchmarks.typical_range}
    </BenchmarkIndicator>
  </BudgetSummary>

  {/* Breakdown Chart - Pie or Bar Chart */}
  <BudgetBreakdownChart>
    {Object.entries(budget.breakdown).map(([category, data]) => (
      <BreakdownItem key={category}>
        <CategoryName>{formatCategoryName(category)}</CategoryName>
        <Amount>€{formatNumber(data.amount)}</Amount>
        <Percentage>{data.percentage}%</Percentage>
        <ProgressBar value={data.percentage} />
      </BreakdownItem>
    ))}
  </BudgetBreakdownChart>

  {/* Effort Summary */}
  <EffortSummary>
    <EffortItem>
      <Label>Total Person-Months</Label>
      <Value>{budget.effort_summary.total_person_months} PM</Value>
    </EffortItem>
    <EffortItem>
      <Label>PM per Partner</Label>
      <Value>{budget.effort_summary.person_months_per_partner} PM</Value>
    </EffortItem>
    <EffortItem>
      <Label>Average PM Cost</Label>
      <Value>€{formatNumber(budget.effort_summary.avg_pm_cost_used)}</Value>
    </EffortItem>
  </EffortSummary>

  {/* Recommendations */}
  <Recommendations>
    <SectionTitle>💡 Recommendations</SectionTitle>
    {budget.recommendations.map((rec, i) => (
      <RecommendationItem key={i}>• {rec}</RecommendationItem>
    ))}
  </Recommendations>
</BudgetCalculationResult>
```

---

## 5. NEW: Timeline Generator Results Display

When the `generate_timeline` tool is used, display a Gantt-like timeline:

### 5.1 Timeline Response Structure

```typescript
interface TimelineGeneration {
  success: boolean;
  tool_name: 'generate_timeline';
  project_title: string;
  parameters: {
    action_type: string;
    duration_months: number;
    num_partners: number;
    total_person_months: number;
  };
  work_packages: Array<{
    number: number;
    title: string;
    lead: string;
    start_month: number;
    end_month: number;
    duration_months: number;
    effort_pms: number;
    effort_percentage: number;
  }>;
  deliverables: Array<{
    id: string;           // e.g., "D2.1"
    seq_id: string;       // e.g., "D1" (sequential)
    title: string;
    wp: number;
    type: string;         // 'R', 'DEM', 'DEC', 'DATA', 'DMP', 'ETHICS', 'OTHER'
    type_description: string;
    dissemination_level: string;  // 'PU', 'SEN', 'CO'
    due_month: number;
  }>;
  milestones: Array<{
    id: string;           // e.g., "MS1"
    title: string;
    related_wp: number;
    due_month: number;
    verification_means: string;
  }>;
  gantt_data: {
    rows: Array<{
      id: string;
      label: string;
      start_month: number;
      end_month: number;
      effort: number;
      bar: string;  // Text-based bar representation
    }>;
  };
  summary: {
    total_wps: number;
    total_deliverables: number;
    total_milestones: number;
    effort_distribution: Record<string, number>;
  };
  recommendations: string[];
}
```

### 5.2 Timeline Display Component (Gantt Chart)

```tsx
<TimelineResult>
  {/* Project Header */}
  <TimelineHeader>
    <ProjectTitle>{timeline.project_title}</ProjectTitle>
    <ProjectMeta>
      <span>{timeline.parameters.action_type}</span>
      <span>{timeline.parameters.duration_months} months</span>
      <span>{timeline.parameters.num_partners} partners</span>
      <span>{timeline.parameters.total_person_months} PM</span>
    </ProjectMeta>
  </TimelineHeader>

  {/* Gantt Chart */}
  <GanttChart duration={timeline.parameters.duration_months}>
    {/* Month headers */}
    <GanttHeader>
      {Array.from({ length: timeline.parameters.duration_months }, (_, i) => (
        <MonthLabel key={i}>M{i + 1}</MonthLabel>
      ))}
    </GanttHeader>

    {/* Work Package rows */}
    {timeline.work_packages.map(wp => (
      <GanttRow key={wp.number}>
        <RowLabel>
          <WPNumber>WP{wp.number}</WPNumber>
          <WPTitle>{wp.title}</WPTitle>
          <WPLead>{wp.lead}</WPLead>
        </RowLabel>
        <GanttBar
          start={wp.start_month}
          end={wp.end_month}
          effort={wp.effort_pms}
          color={getWPColor(wp.number)}
        />
      </GanttRow>
    ))}

    {/* Milestone markers */}
    {timeline.milestones.map(ms => (
      <MilestoneMarker
        key={ms.id}
        month={ms.due_month}
        label={ms.id}
        title={ms.title}
      />
    ))}

    {/* Deliverable markers */}
    {timeline.deliverables.map(d => (
      <DeliverableMarker
        key={d.seq_id}
        month={d.due_month}
        label={d.seq_id}
        type={d.type}
      />
    ))}
  </GanttChart>

  {/* Deliverables Table */}
  <DeliverablesList>
    <SectionTitle>📄 Deliverables ({timeline.summary.total_deliverables})</SectionTitle>
    <Table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Title</th>
          <th>WP</th>
          <th>Type</th>
          <th>Due</th>
          <th>Level</th>
        </tr>
      </thead>
      <tbody>
        {timeline.deliverables.map(d => (
          <tr key={d.seq_id}>
            <td>{d.seq_id}</td>
            <td>{d.title}</td>
            <td>WP{d.wp}</td>
            <td><TypeBadge type={d.type}>{d.type_description}</TypeBadge></td>
            <td>M{d.due_month}</td>
            <td><LevelBadge level={d.dissemination_level} /></td>
          </tr>
        ))}
      </tbody>
    </Table>
  </DeliverablesList>

  {/* Milestones List */}
  <MilestonesList>
    <SectionTitle>🎯 Milestones ({timeline.summary.total_milestones})</SectionTitle>
    {timeline.milestones.map(ms => (
      <MilestoneItem key={ms.id}>
        <MilestoneId>{ms.id}</MilestoneId>
        <MilestoneTitle>{ms.title}</MilestoneTitle>
        <MilestoneDue>M{ms.due_month}</MilestoneDue>
      </MilestoneItem>
    ))}
  </MilestonesList>

  {/* Recommendations */}
  <Recommendations>
    <SectionTitle>💡 Recommendations</SectionTitle>
    {timeline.recommendations.map((rec, i) => (
      <RecommendationItem key={i}>• {rec}</RecommendationItem>
    ))}
  </Recommendations>
</TimelineResult>
```

---

## 6. Enhanced Funding Call Display

The V3ResponseFormatter now provides rich formatting. Parse and enhance it:

### 6.1 Call Response Structure (from Markdown)

The backend returns formatted markdown. Parse these patterns:

```typescript
// Pattern matching for call blocks
const CALL_PATTERNS = {
  title: /\*\*(\d+)\.\s+(.+?)\*\*/,
  callId: /📋 \*\*Call ID:\*\* (.+)/,
  type: /([🔬🚀🤝💱🎓👨‍🔬📦🔧🛒]) \*\*Type:\*\* (\w+)/,
  status: /([🟢🟡🔴]) \*\*Status:\*\* (\w+)/,
  deadline: /⏰ \*\*Deadline:\*\* (.+)/,
  programme: /🏛️ \*\*Programme:\*\* (.+)/,
  budget: /💰 \*\*Budget:\*\* (.+)/,
  scope: /\*\*Scope:\*\* (.+)/,
  applyLink: /🔗 \*\*Apply:\*\* (.+)/,
};

// Type icons mapping
const TYPE_ICONS: Record<string, string> = {
  'RIA': '🔬',
  'IA': '🚀',
  'CSA': '🤝',
  'COFUND': '💱',
  'ERC': '🎓',
  'MSCA': '👨‍🔬',
  'LUMP-SUM': '📦',
  'PCP': '🔧',
  'PPI': '🛒',
};

// Status icons mapping
const STATUS_ICONS: Record<string, string> = {
  'open': '🟢',
  'upcoming': '🟡',
  'closed': '🔴',
};
```

### 6.2 Call Card Component

```tsx
<FundingCallCard>
  <CallHeader>
    <CallNumber>{call.number}</CallNumber>
    <CallTitle>{call.title}</CallTitle>
    <StatusBadge status={call.status}>
      {STATUS_ICONS[call.status]} {call.status}
    </StatusBadge>
  </CallHeader>

  <CallMeta>
    <MetaItem icon="📋" label="Call ID" value={call.callId} copyable />
    <MetaItem icon={TYPE_ICONS[call.type]} label="Type" value={call.type} />
    <MetaItem icon="⏰" label="Deadline" value={call.deadline} highlight={isUrgent(call.deadline)} />
    <MetaItem icon="🏛️" label="Programme" value={call.programme} />
    <MetaItem icon="💰" label="Budget" value={call.budget} />
  </CallMeta>

  <CallScope>
    <ScopeText>{call.scope}</ScopeText>
  </CallScope>

  <CallActions>
    <ApplyButton href={call.applyLink} target="_blank">
      🔗 Apply on EU Portal
    </ApplyButton>
    <SaveButton onClick={() => saveCall(call)}>
      ⭐ Save
    </SaveButton>
  </CallActions>
</FundingCallCard>
```

---

## 7. Enhanced Project Display (with Publications & Deliverables)

### 7.1 Project Response Structure

Projects now include publications, deliverables, and impact metrics:

```typescript
interface EnhancedProject {
  title: string;
  acronym: string;
  id: string;
  programme: string;
  status: string;
  startDate: string;
  endDate: string;
  ecMaxContribution: number;
  coordinator: string;
  objective: string;

  // NEW: Enhanced data
  publications?: Array<{
    title: string;
    authors: string;
    journal?: string;
    doi?: string;
  }>;
  deliverables?: Array<{
    title: string;
    type: string;
    url?: string;
  }>;
  impact_metrics?: {
    publications_count: number;
    deliverables_count: number;
    patents_count: number;
    datasets_count: number;
  };
}
```

### 7.2 Project Card Component

```tsx
<ProjectCard>
  <ProjectHeader>
    <Acronym>{project.acronym}</Acronym>
    <Title>{project.title}</Title>
    <StatusBadge status={project.status}>
      {project.status === 'ongoing' ? '🟢' : '✅'} {project.status}
    </StatusBadge>
  </ProjectHeader>

  <ProjectMeta>
    <MetaItem icon="🔢" label="Project ID" value={project.id} />
    <MetaItem icon="🏛️" label="Programme" value={project.programme} />
    <MetaItem icon="📅" label="Duration" value={`${project.startDate} → ${project.endDate}`} />
    <MetaItem icon="💰" label="EU Contribution" value={formatBudget(project.ecMaxContribution)} />
    <MetaItem icon="🏢" label="Coordinator" value={project.coordinator} />
  </ProjectMeta>

  <Objective>
    <SectionTitle>Objective</SectionTitle>
    <ObjectiveText>{project.objective}</ObjectiveText>
  </Objective>

  {/* NEW: Publications Section */}
  {project.publications && project.publications.length > 0 && (
    <Publications>
      <SectionTitle>📚 Key Publications</SectionTitle>
      {project.publications.map((pub, i) => (
        <PublicationItem key={i}>
          <PubTitle>{pub.title}</PubTitle>
          <PubAuthors>{pub.authors}</PubAuthors>
          {pub.journal && <PubJournal>{pub.journal}</PubJournal>}
          {pub.doi && (
            <DOILink href={`https://doi.org/${pub.doi}`} target="_blank">
              DOI: {pub.doi}
            </DOILink>
          )}
        </PublicationItem>
      ))}
    </Publications>
  )}

  {/* NEW: Deliverables Section */}
  {project.deliverables && project.deliverables.length > 0 && (
    <Deliverables>
      <SectionTitle>📦 Key Deliverables</SectionTitle>
      {project.deliverables.map((del, i) => (
        <DeliverableItem key={i}>
          <DelTitle>{del.title}</DelTitle>
          <DelType>{del.type}</DelType>
          {del.url && (
            <ViewLink href={del.url} target="_blank">View</ViewLink>
          )}
        </DeliverableItem>
      ))}
    </Deliverables>
  )}

  {/* NEW: Impact Metrics */}
  {project.impact_metrics && (
    <ImpactMetrics>
      <SectionTitle>📊 Impact</SectionTitle>
      <MetricsGrid>
        <Metric icon="📚" value={project.impact_metrics.publications_count} label="Publications" />
        <Metric icon="📦" value={project.impact_metrics.deliverables_count} label="Deliverables" />
        <Metric icon="📜" value={project.impact_metrics.patents_count} label="Patents" />
        <Metric icon="💾" value={project.impact_metrics.datasets_count} label="Datasets" />
      </MetricsGrid>
    </ImpactMetrics>
  )}

  <ProjectActions>
    <CordisLink href={`https://cordis.europa.eu/project/id/${project.id}`} target="_blank">
      🔗 View on CORDIS
    </CordisLink>
  </ProjectActions>
</ProjectCard>
```

---

## 8. Response Metadata Display

### 8.1 Metadata from Complete Event

```typescript
interface ResponseMetadata {
  architecture: 'simplified_v3';
  tools_used: string[];
  iterations: number;
  total_time_ms: number;
  cache_hit?: boolean;        // NEW: from plan caching
  speculative_hits?: number;  // NEW: from speculative execution
}
```

### 8.2 Metadata Display Component

```tsx
<ResponseMetadata>
  <MetadataItem>
    <Label>Tools Used</Label>
    <ToolsList>
      {metadata.tools_used.map(tool => (
        <ToolBadge key={tool}>
          {TOOL_DISPLAY_CONFIG[tool]?.icon} {TOOL_DISPLAY_CONFIG[tool]?.label}
        </ToolBadge>
      ))}
    </ToolsList>
  </MetadataItem>

  <MetadataItem>
    <Label>Response Time</Label>
    <Value>{(metadata.total_time_ms / 1000).toFixed(1)}s</Value>
  </MetadataItem>

  {metadata.cache_hit && (
    <MetadataItem>
      <CacheHitBadge>⚡ Cached response</CacheHitBadge>
    </MetadataItem>
  )}

  <MetadataItem>
    <Label>Iterations</Label>
    <Value>{metadata.iterations}</Value>
  </MetadataItem>
</ResponseMetadata>
```

---

## 9. State Management Recommendations

### 9.1 Conversation State

```typescript
interface ConversationState {
  conversationId: string;
  messages: Message[];
  isStreaming: boolean;
  currentToolExecution: ToolExecution | null;
  agentThinking: string | null;
  feedback: Record<string, FeedbackSubmission>;  // messageId -> feedback
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: ResponseMetadata;
  toolsUsed?: string[];
  feedbackSubmitted?: boolean;
}
```

### 9.2 Actions

```typescript
type ConversationAction =
  | { type: 'SEND_MESSAGE'; payload: string }
  | { type: 'STREAM_TOKEN'; payload: string }
  | { type: 'STREAM_COMPLETE'; payload: ResponseMetadata }
  | { type: 'TOOL_EXECUTING'; payload: { tool: string; args: any } }
  | { type: 'TOOL_COMPLETED'; payload: { tool: string; result: any } }
  | { type: 'AGENT_THINKING'; payload: string }
  | { type: 'SUBMIT_FEEDBACK'; payload: FeedbackSubmission }
  | { type: 'CLEAR_CONVERSATION' }
  | { type: 'SET_ERROR'; payload: string };
```

---

## 10. Styling Recommendations

### 10.1 Color Palette for Tool Status

```css
:root {
  /* Tool execution states */
  --tool-executing: #3b82f6;    /* Blue - in progress */
  --tool-success: #10b981;      /* Green - completed */
  --tool-failed: #ef4444;       /* Red - failed */

  /* Feedback states */
  --feedback-positive: #10b981; /* Green */
  --feedback-negative: #ef4444; /* Red */
  --feedback-neutral: #6b7280;  /* Gray */

  /* Call status */
  --status-open: #10b981;       /* Green */
  --status-upcoming: #f59e0b;   /* Yellow */
  --status-closed: #ef4444;     /* Red */

  /* Budget benchmark */
  --benchmark-within: #10b981;  /* Green - within range */
  --benchmark-below: #f59e0b;   /* Yellow - below typical */
  --benchmark-above: #ef4444;   /* Red - above typical */
}
```

### 10.2 Animation Suggestions

```css
/* Tool execution pulse */
@keyframes tool-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.tool-executing {
  animation: tool-pulse 1.5s ease-in-out infinite;
}

/* Agent thinking animation */
@keyframes thinking-dots {
  0%, 20% { content: '.'; }
  40% { content: '..'; }
  60%, 100% { content: '...'; }
}

.agent-thinking::after {
  animation: thinking-dots 1.5s infinite;
}

/* Gantt bar grow animation */
@keyframes gantt-grow {
  from { width: 0; }
  to { width: 100%; }
}

.gantt-bar {
  animation: gantt-grow 0.5s ease-out forwards;
}
```

---

## 11. Error Handling

### 11.1 Error Types

```typescript
type APIError =
  | { code: 'RATE_LIMITED'; retryAfter: number }
  | { code: 'TOOL_FAILED'; tool: string; message: string }
  | { code: 'STREAM_INTERRUPTED'; lastMessage: string }
  | { code: 'FEEDBACK_FAILED'; message: string }
  | { code: 'SERVER_ERROR'; message: string };
```

### 11.2 Error Display

```tsx
<ErrorBoundary fallback={<ErrorFallback />}>
  <ConversationView />
</ErrorBoundary>

// Tool-specific error
{toolError && (
  <ToolError>
    <ErrorIcon>⚠️</ErrorIcon>
    <ErrorMessage>
      {TOOL_DISPLAY_CONFIG[toolError.tool]?.label} failed: {toolError.message}
    </ErrorMessage>
    <RetryButton onClick={retryTool}>Retry</RetryButton>
  </ToolError>
)}
```

---

## 12. Accessibility Considerations

1. **Screen Reader Support**: Add ARIA labels to all interactive elements
2. **Keyboard Navigation**: Ensure all actions are keyboard accessible
3. **Color Contrast**: Use sufficient contrast for status indicators
4. **Focus Management**: Manage focus during streaming and tool execution
5. **Loading States**: Announce loading states to screen readers

```tsx
<ToolExecution
  aria-live="polite"
  aria-busy={status === 'executing'}
  role="status"
>
  <span className="sr-only">
    {status === 'executing'
      ? `Executing ${toolLabel}`
      : `${toolLabel} completed`}
  </span>
  {/* Visual content */}
</ToolExecution>
```

---

## 13. Testing Checklist

Before deployment, verify:

- [ ] Feedback widget appears after each AI response
- [ ] Feedback submission works (check network tab)
- [ ] Tool execution displays correctly during streaming
- [ ] Budget calculator results render with charts
- [ ] Timeline generator shows Gantt chart
- [ ] Publications and deliverables appear in project cards
- [ ] All 20 tools have correct icons and labels
- [ ] Error states display appropriately
- [ ] Keyboard navigation works throughout
- [ ] Mobile responsive design works

---

## 14. API Response Examples

### 14.1 Feedback Summary Response

```json
GET /api/feedback/summary

{
  "total_feedback": 156,
  "average_rating": 4.2,
  "helpful_count": 98,
  "not_helpful_count": 23,
  "incorrect_count": 12,
  "incomplete_count": 18,
  "other_count": 5,
  "satisfaction_rate": 78.5,
  "period_days": 7
}
```

### 14.2 Tool Performance Response

```json
GET /api/feedback/suggestions

{
  "suggestions": [
    "Consider improving search_projects response time (avg 450ms)",
    "get_call_details has lower satisfaction (3.8) - review output format"
  ],
  "underperforming_tools": [
    {"tool": "get_call_details", "avg_rating": 3.8, "usage_count": 45}
  ],
  "issue_patterns": [
    {"feedback_type": "incomplete", "count": 18}
  ],
  "generated_at": "2025-12-03T18:00:00Z"
}
```

---

## Questions?

Contact the backend team for:
- API clarifications
- WebSocket support for real-time analytics
- Custom tool output formats
- Performance optimization recommendations
