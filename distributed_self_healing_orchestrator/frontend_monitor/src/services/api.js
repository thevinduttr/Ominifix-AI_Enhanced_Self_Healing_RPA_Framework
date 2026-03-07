export async function fetchBotStatus() {
  const response = await fetch('/status')
  if (!response.ok) {
    throw new Error('Network response was not ok')
  }
  return await response.json()
}

export async function sendToElementLocatorEngine(failure) {
  const payload = {
    page_url: failure.page_url || 'about:blank',
    failure_type: failure.failure_type || failure.category || 'ELEMENT_NOT_VISIBLE',
    failed_action: failure.failed_action || failure.last_action || 'click',
    element_role: failure.element_role || null,
    expected_text: failure.expected_text || null,
    old_locator: failure.old_locator || null,
    old_locator_type: failure.old_locator_type || null,
    error_message: failure.error || failure.error_message || null,
    page_html: failure.page_html || failure.dom || null,
    screenshot_path: failure.screenshot_path || null,
    template_path: failure.template_path || null,
    metadata: {
      ...(failure.metadata || {}),
      source: 'frontend_monitor',
      bot_id: failure.botId || null,
      classification: failure.category || failure.failure_type || null,
    },
  }

  const response = await fetch('/element-locator/report', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`Locator engine request failed: ${response.status} ${text}`)
  }

  return await response.json()
}

export async function sendToHealingEngineDirect(failure) {
  const payload = {
    metadata: {
      schema_version: '1.0',
      report_id: `DIRECT-${Date.now()}`,
      run_id: failure?.metadata?.run_id || '',
      bot_id: failure.botId || failure?.metadata?.bot_id || 'UNKNOWN_BOT',
      timestamp: new Date().toISOString(),
      source_component: 'frontend_monitor',
      target_component: 'code_healing_engine',
      environment: failure?.metadata?.environment || 'docker',
    },
    failure_context: {
      script_path: failure?.metadata?.script_path || 'data/scripts/broken/auto_generated.py',
      failing_line: Number(failure?.metadata?.failing_line || 1),
      action: failure.failed_action || failure.last_action || 'authenticate_user',
      old_locator: failure.old_locator || '',
      error_type: failure.failure_type || failure.category || 'AUTHENTICATION_ERROR',
      error_message: failure.error || failure.error_message || 'Authentication failed',
    },
    dom_context: {
      new_element_html: failure.page_html || failure.dom || '',
      page_url: failure.page_url || failure?.metadata?.target_url || '',
      page_name: failure?.metadata?.page_name || '',
    },
    element_expectation: {
      expected_role: failure.element_role || 'login_form',
      expected_text: failure.expected_text || 'Login',
    },
    element_candidate: null,
  }

  const response = await fetch('/healing-direct', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`Healing engine direct request failed: ${response.status} ${text}`)
  }

  return await response.json()
}
