import { NextRequest, NextResponse } from 'next/server'

const BACKEND_BASE = 'http://localhost:8002/api/v1'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ meetingId: string }> }
) {
  try {
    const { meetingId } = await params
    
    const response = await fetch(`${BACKEND_BASE}/meetings/${meetingId}/mom`, {
      headers: { 'x-api-key': 'dev-unprotected' }
    })
    
    if (!response.ok) {
      return NextResponse.json(null)
    }
    
    const data = await response.json()
    return NextResponse.json(data)
  } catch (error: any) {
    console.error('[API Proxy] MoM Error:', error.message)
    return NextResponse.json(null)
  }
}
