import { NextResponse } from 'next/server'

const BACKEND_BASE = 'http://localhost:8002/api/v1'

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_BASE}/followups`, {
      headers: { 'x-api-key': 'dev-unprotected' }
    })
    
    if (!response.ok) {
      return NextResponse.json({ error: 'Failed to fetch' }, { status: response.status })
    }
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('[API Proxy] Followups Error:', error.message)
    return NextResponse.json({ error: error.message }, { status: 500 })
  }
}
