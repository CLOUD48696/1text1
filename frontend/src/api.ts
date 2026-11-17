export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, body === undefined ? undefined : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  if (!response.ok) {
    const problem = await response.json().catch(() => ({}))
    throw new Error(problem.message || '请求失败，请稍后重试')
  }
  return response.json()
}
