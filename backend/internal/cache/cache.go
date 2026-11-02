// Package cache provides a thread-safe in-memory cache with optional expiry.
package cache

import (
	"sync"
	"time"
)

// Options configures expiry and size limits. Zero values disable each feature.
type Options struct {
	// TTL is how long a value is considered fresh.
	TTL time.Duration
	// StaleFor is how long after TTL a value may still be served when a reload
	// fails, so a brief upstream outage does not reach the user.
	StaleFor time.Duration
	// MaxEntries bounds memory use; the oldest entry is evicted when exceeded.
	MaxEntries int
}

type entry[T any] struct {
	value    T
	storedAt time.Time
}

type inflight[T any] struct {
	done  chan struct{}
	value T
	err   error
}

// Cache stores values by string key and allows concurrent reads.
type Cache[T any] struct {
	mu      sync.RWMutex
	opts    Options
	values  map[string]entry[T]
	loading map[string]*inflight[T]
	now     func() time.Time
}

// New creates a cache whose values never expire.
func New[T any]() *Cache[T] {
	return NewWithOptions[T](Options{})
}

// NewWithOptions creates a cache with the given expiry and size limits.
func NewWithOptions[T any](opts Options) *Cache[T] {
	return &Cache[T]{
		opts:    opts,
		values:  make(map[string]entry[T]),
		loading: make(map[string]*inflight[T]),
		now:     time.Now,
	}
}

// Get returns the fresh value associated with key.
func (c *Cache[T]) Get(key string) (T, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.freshLocked(key)
}

// Set stores value for key, replacing any previous value.
func (c *Cache[T]) Set(key string, value T) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.setLocked(key, value)
}

// GetOrLoad returns the fresh value for key or calls load to produce it.
// Concurrent callers for the same key share a single load. If load fails and an
// expired value is still inside the StaleFor window, that value is returned.
func (c *Cache[T]) GetOrLoad(key string, load func() (T, error)) (T, error) {
	c.mu.Lock()
	if value, ok := c.freshLocked(key); ok {
		c.mu.Unlock()
		return value, nil
	}
	if call, ok := c.loading[key]; ok {
		c.mu.Unlock()
		<-call.done
		return call.value, call.err
	}
	call := &inflight[T]{done: make(chan struct{})}
	c.loading[key] = call
	c.mu.Unlock()

	// The deferred cleanup also releases waiters if load panics.
	defer func() {
		c.mu.Lock()
		delete(c.loading, key)
		c.mu.Unlock()
		close(call.done)
	}()

	call.value, call.err = load()

	c.mu.Lock()
	defer c.mu.Unlock()
	if call.err == nil {
		c.setLocked(key, call.value)
	} else if stale, ok := c.staleLocked(key); ok {
		call.value, call.err = stale, nil
	}
	return call.value, call.err
}

func (c *Cache[T]) freshLocked(key string) (T, bool) {
	item, ok := c.values[key]
	if !ok || (c.opts.TTL > 0 && c.now().Sub(item.storedAt) >= c.opts.TTL) {
		var zero T
		return zero, false
	}
	return item.value, true
}

func (c *Cache[T]) staleLocked(key string) (T, bool) {
	item, ok := c.values[key]
	if !ok || c.now().Sub(item.storedAt) >= c.opts.TTL+c.opts.StaleFor {
		var zero T
		return zero, false
	}
	return item.value, true
}

func (c *Cache[T]) setLocked(key string, value T) {
	c.values[key] = entry[T]{value: value, storedAt: c.now()}
	if c.opts.MaxEntries > 0 && len(c.values) > c.opts.MaxEntries {
		c.evictOldestLocked()
	}
}

func (c *Cache[T]) evictOldestLocked() {
	var oldestKey string
	var oldest time.Time
	for key, item := range c.values {
		if oldestKey == "" || item.storedAt.Before(oldest) {
			oldestKey, oldest = key, item.storedAt
		}
	}
	delete(c.values, oldestKey)
}
