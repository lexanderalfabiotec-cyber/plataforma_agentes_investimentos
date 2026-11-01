// Package cache provides a thread-safe in-memory cache.
package cache

import "sync"

// Cache stores values by string key and allows concurrent reads.
type Cache[T any] struct {
	mu     sync.RWMutex
	values map[string]T
}

// New creates an initialized cache.
func New[T any]() *Cache[T] {
	return &Cache[T]{values: make(map[string]T)}
}

// Get returns the value associated with key.
func (c *Cache[T]) Get(key string) (T, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	value, ok := c.values[key]
	return value, ok
}

// Set stores value for key, replacing any previous value.
func (c *Cache[T]) Set(key string, value T) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.values[key] = value
}
