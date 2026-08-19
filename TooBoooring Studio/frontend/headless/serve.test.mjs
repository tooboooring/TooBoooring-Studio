import assert from 'node:assert/strict'
import test from 'node:test'
import { resolveHost } from './serve.mjs'

test('resolveHost defaults to the loopback address', () => {
  assert.equal(resolveHost({}, {}), '127.0.0.1')
})

test('resolveHost accepts TOOBOOORING_STUDIO_HOST', () => {
  assert.equal(resolveHost({}, { TOOBOOORING_STUDIO_HOST: '0.0.0.0' }), '0.0.0.0')
})

test('resolveHost accepts --host', () => {
  assert.equal(resolveHost({ host: '192.0.2.10' }, {}), '192.0.2.10')
})

test('--host takes precedence over TOOBOOORING_STUDIO_HOST', () => {
  assert.equal(resolveHost({ host: '127.0.0.2' }, { TOOBOOORING_STUDIO_HOST: '0.0.0.0' }), '127.0.0.2')
})

test('resolveHost rejects empty and missing option values', () => {
  assert.throws(() => resolveHost({ host: '' }, {}), /non-empty string/)
  assert.throws(() => resolveHost({ host: '   ' }, {}), /non-empty string/)
  assert.throws(() => resolveHost({ host: true }, {}), /non-empty string/)
  assert.throws(() => resolveHost({}, { TOOBOOORING_STUDIO_HOST: '' }), /non-empty string/)
})
