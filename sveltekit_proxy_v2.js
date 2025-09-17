// Updated SvelteKit proxy for Context-Aware AI System v2
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ params, request, fetch }) => {
  const conversationId = params.conversation_id;
  
  try {
    // Updated to use v2 endpoints with enhanced features
    const backendUrl = `${process.env.BACKEND_URL || 'http://localhost:8001'}/api/v2/conversation/${conversationId}/message/stream`;
    
    const body = await request.text();
    
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body
    });
    
    if (!response.ok) {
      throw error(response.status, `Backend error: ${response.statusText}`);
    }
    
    // Return the enhanced streaming response with memory and citations
    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': '*',
      }
    });
    
  } catch (err) {
    console.error('Proxy error:', err);
    throw error(500, 'Failed to proxy streaming request');
  }
};

// Additional endpoint for memory management
export const GET: RequestHandler = async ({ params, fetch }) => {
  const conversationId = params.conversation_id;
  
  try {
    const backendUrl = `${process.env.BACKEND_URL || 'http://localhost:8001'}/api/v2/conversation/${conversationId}/memory`;
    
    const response = await fetch(backendUrl);
    
    if (!response.ok) {
      throw error(response.status, `Backend error: ${response.statusText}`);
    }
    
    const memoryData = await response.json();
    
    return new Response(JSON.stringify(memoryData), {
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
  } catch (err) {
    console.error('Memory fetch error:', err);
    throw error(500, 'Failed to fetch conversation memory');
  }
};

// Health check endpoint
export const HEAD: RequestHandler = async ({ fetch }) => {
  try {
    const backendUrl = `${process.env.BACKEND_URL || 'http://localhost:8001'}/api/v2/conversation/health`;
    
    const response = await fetch(backendUrl);
    
    return new Response(null, {
      status: response.ok ? 200 : 503,
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
  } catch (err) {
    return new Response(null, { status: 503 });
  }
};