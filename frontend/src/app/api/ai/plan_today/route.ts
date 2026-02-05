import { NextRequest, NextResponse } from 'next/server'

const BACKEND_BASE = 'http://localhost:8002/api/v1'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    const response = await fetch(`${BACKEND_BASE}/ai/plan_today`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'x-api-key': 'dev-unprotected' 
      },
      body: JSON.stringify(body)
    })
    
    if (!response.ok) {
      return NextResponse.json({ error: 'Failed to generate plan' }, { status: response.status })
    }
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('[API Proxy] Plan Today Error:', error.message)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}
