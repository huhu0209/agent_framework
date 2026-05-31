/**
 * Collapsible agent configuration form.
 *
 * Always-visible fields: Name, Role.
 * Collapsible field: System Prompt (hidden by default).
 * Dispatches UPDATE_FORM on change.
 */

import { useState } from 'react';
import { useAppState } from '../../state/context';

export function ConfigForm() {
  const { state, dispatch } = useAppState();
  const [showPrompt, setShowPrompt] = useState(false);

  const updateField = (field: string, value: string) => {
    dispatch({ type: 'UPDATE_FORM', field, value });
  };

  return (
    <div style={{ padding: '16px' }}>
      <h2
        style={{
          fontSize: '16px',
          fontWeight: 600,
          fontFamily: 'system-ui',
          color: '#141413',
          marginBottom: '12px',
        }}
      >
        Agent Config
      </h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {/* Name */}
        <div>
          <label
            style={{
              display: 'block',
              fontSize: '14px',
              fontFamily: 'system-ui',
              color: '#5e5d59',
              marginBottom: '4px',
            }}
          >
            Name
          </label>
          <input
            type="text"
            required
            value={state.formData.name}
            onChange={(e) => updateField('name', e.target.value)}
            style={{
              width: '100%',
              height: '32px',
              padding: '0 12px',
              fontSize: '14px',
              fontFamily: 'system-ui',
              color: '#141413',
              backgroundColor: '#faf9f5',
              border: '1px solid #f0eee6',
              borderRadius: '12px',
              outline: 'none',
              boxSizing: 'border-box',
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = '#3898ec';
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = '#f0eee6';
            }}
          />
        </div>

        {/* Role */}
        <div>
          <label
            style={{
              display: 'block',
              fontSize: '14px',
              fontFamily: 'system-ui',
              color: '#5e5d59',
              marginBottom: '4px',
            }}
          >
            Role
          </label>
          <input
            type="text"
            required
            value={state.formData.role}
            onChange={(e) => updateField('role', e.target.value)}
            style={{
              width: '100%',
              height: '32px',
              padding: '0 12px',
              fontSize: '14px',
              fontFamily: 'system-ui',
              color: '#141413',
              backgroundColor: '#faf9f5',
              border: '1px solid #f0eee6',
              borderRadius: '12px',
              outline: 'none',
              boxSizing: 'border-box',
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = '#3898ec';
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = '#f0eee6';
            }}
          />
        </div>

        {/* System Prompt toggle */}
        <button
          type="button"
          onClick={() => setShowPrompt(!showPrompt)}
          style={{
            background: 'none',
            border: 'none',
            padding: 0,
            fontSize: '14px',
            fontFamily: 'system-ui',
            color: '#c96442',
            cursor: 'pointer',
            textDecoration: showPrompt ? 'underline' : 'none',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.textDecoration = 'underline';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.textDecoration = showPrompt
              ? 'underline'
              : 'none';
          }}
        >
          {showPrompt ? 'Hide System Prompt' : 'Show System Prompt'}
        </button>

        {/* System Prompt textarea (collapsible) */}
        {showPrompt && (
          <textarea
            value={state.formData.systemPrompt}
            onChange={(e) => updateField('systemPrompt', e.target.value)}
            placeholder="Optional system prompt..."
            rows={4}
            style={{
              width: '100%',
              padding: '6px 12px',
              fontSize: '14px',
              fontFamily: 'system-ui',
              color: '#141413',
              backgroundColor: '#faf9f5',
              border: '1px solid #f0eee6',
              borderRadius: '12px',
              outline: 'none',
              resize: 'vertical',
              boxSizing: 'border-box',
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = '#3898ec';
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = '#f0eee6';
            }}
          />
        )}
      </div>
    </div>
  );
}
