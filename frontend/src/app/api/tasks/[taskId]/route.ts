import { NextRequest, NextResponse } from 'next/server'

const BACKEND_BASE = 'http://localhost:8002/api/v1'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> }
) {
  try {
    const { taskId } = await params
    
    const response = await fetch(`${BACKEND_BASE}/tasks/${taskId}`, {
      headers: { 'x-api-key': 'dev-unprotected' }
    })
    
    if (!response.ok) {
      return NextResponse.json({ error: 'Task not found' }, { status: response.status })
    }
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('[API Proxy] Task Error:', error.message)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> }
) {
  try {
    const { taskId } = await params
    const body = await request.json()
    
    const response = await fetch(`${BACKEND_BASE}/tasks/${taskId}`, {
      method: 'PATCH',
      headers: { 
        'Content-Type': 'application/json',
        'x-api-key': 'dev-unprotected' 
      },
      body: JSON.stringify(body)
    })
    
    if (!response.ok) {
      return NextResponse.json({ error: 'Failed to update task' }, { status: response.status })
    }
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('[API Proxy] Task PATCH Error:', error.message)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> }
) {
  try {
    const { taskId } = await params
    const body = await request.json()
    
    const response = await fetch(`${BACKEND_BASE}/tasks/${taskId}`, {
      method: 'PUT',
      headers: { 
        'Content-Type': 'application/json',
        'x-api-key': 'dev-unprotected' 
      },
      body: JSON.stringify(body)
    })
    
    if (!response.ok) {
      return NextResponse.json({ error: 'Failed to update task' }, { status: response.status })
    }
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('[API Proxy] Task PUT Error:', error.message)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> }
) {
  try {
    const { taskId } = await params
    
    const response = await fetch(`${BACKEND_BASE}/tasks/${taskId}`, {
      method: 'DELETE',
      headers: { 'x-api-key': 'dev-unprotected' }
    })
    
    if (!response.ok) {
      return NextResponse.json({ error: 'Failed to delete task' }, { status: response.status })
    }
    
    return NextResponse.json({ status: 'deleted' })
  } catch (error: any) {
    console.error('[API Proxy] Task DELETE Error:', error.message)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}
