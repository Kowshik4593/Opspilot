import { NextResponse } from 'next/server'

const BACKEND_BASE = 'http://localhost:8002/api/v1'

export async function POST() {
  try {
    const response = await fetch(`${BACKEND_BASE}/autonomous/stop`, {
      method: 'POST',
      headers: { 'x-api-key': 'dev-unprotected' }
    })
    
    if (!response.ok) {
      return NextResponse.json({ success: false }, { status: response.status })
    }
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('[API Proxy] Autonomous Stop Error:', error.message)
    return NextResponse.json({ success: false, error: error.message }, { status: 500 })
  }
}
