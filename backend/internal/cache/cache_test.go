package cache

import (
	"fmt"
	"sync"
	"testing"
)

func TestCacheGetAndSet(t *testing.T) {
	c := New[string]()

	if _, ok := c.Get("missing"); ok {
		t.Fatal("Get de chave ausente deve retornar ok=false")
	}

	c.Set("ticker", "first")
	if got, ok := c.Get("ticker"); !ok || got != "first" {
		t.Fatalf("Get = (%q, %v), esperado (%q, true)", got, ok, "first")
	}

	c.Set("ticker", "updated")
	if got, ok := c.Get("ticker"); !ok || got != "updated" {
		t.Fatalf("Get após sobrescrita = (%q, %v), esperado (%q, true)", got, ok, "updated")
	}
}

func TestCacheConcurrentAccess(t *testing.T) {
	c := New[int]()
	const workers = 100

	var wg sync.WaitGroup
	wg.Add(workers)
	for i := range workers {
		go func(i int) {
			defer wg.Done()
			key := fmt.Sprintf("key-%d", i)
			c.Set(key, i)
			if got, ok := c.Get(key); !ok || got != i {
				t.Errorf("Get(%q) = (%d, %v), esperado (%d, true)", key, got, ok, i)
			}
		}(i)
	}
	wg.Wait()
}
