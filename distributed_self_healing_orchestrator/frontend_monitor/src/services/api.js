export async function fetchBotStatus() {
  const response = await fetch('/status')
  if (!response.ok) {
    throw new Error('Network response was not ok')
  }
  return await response.json()
}
