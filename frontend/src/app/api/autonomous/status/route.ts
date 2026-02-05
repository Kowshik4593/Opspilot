import { NextResponse } from 'next/server'

const BACKEND_BASE = 'http://localhost:8002/api/v1'

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_BASE}/autonomous/status`, {
      headers: { 'x-api-key': 'dev-unprotected' }
    })
    
    if (!response.ok) {
      return NextResponse.json({ is_running: false }, { status: 200 })
    }
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('[API Proxy] Autonomous Status Error:', error.message)
    return NextResponse.json({ is_running: false }, { status: 200 })
  }
}
