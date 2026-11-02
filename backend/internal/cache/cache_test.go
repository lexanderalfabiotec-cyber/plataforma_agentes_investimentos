package cache

import (
	"errors"
	"fmt"
	"sync"
	"sync/atomic"
	"testing"
	"time"
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

func newClockedCache(opts Options) (*Cache[string], *time.Time) {
	c := NewWithOptions[string](opts)
	current := time.Unix(1_000_000, 0)
	c.now = func() time.Time { return current }
	return c, &current
}

func TestCacheExpiresAfterTTL(t *testing.T) {
	c, clock := newClockedCache(Options{TTL: time.Minute})
	c.Set("k", "v")

	*clock = clock.Add(59 * time.Second)
	if _, ok := c.Get("k"); !ok {
		t.Fatal("valor ainda dentro do TTL deveria ser retornado")
	}
	*clock = clock.Add(time.Second)
	if _, ok := c.Get("k"); ok {
		t.Fatal("valor com TTL vencido não deveria ser retornado")
	}
}

func TestGetOrLoadUsesCacheUntilExpiry(t *testing.T) {
	c, clock := newClockedCache(Options{TTL: time.Minute})
	calls := 0
	load := func() (string, error) {
		calls++
		return fmt.Sprintf("v%d", calls), nil
	}

	for range 3 {
		if got, err := c.GetOrLoad("k", load); err != nil || got != "v1" {
			t.Fatalf("GetOrLoad = (%q, %v), esperado (v1, nil)", got, err)
		}
	}
	*clock = clock.Add(time.Minute)
	if got, err := c.GetOrLoad("k", load); err != nil || got != "v2" {
		t.Fatalf("após expirar: GetOrLoad = (%q, %v), esperado (v2, nil)", got, err)
	}
}

func TestGetOrLoadServesStaleOnlyInsideWindow(t *testing.T) {
	c, clock := newClockedCache(Options{TTL: time.Minute, StaleFor: time.Minute})
	c.Set("k", "antigo")
	failure := errors.New("yahoo fora do ar")
	fail := func() (string, error) { return "", failure }

	*clock = clock.Add(90 * time.Second)
	if got, err := c.GetOrLoad("k", fail); err != nil || got != "antigo" {
		t.Fatalf("dentro da janela: GetOrLoad = (%q, %v), esperado (antigo, nil)", got, err)
	}

	*clock = clock.Add(30 * time.Second)
	if _, err := c.GetOrLoad("k", fail); !errors.Is(err, failure) {
		t.Fatalf("fora da janela: erro = %v, esperado %v", err, failure)
	}
}

func TestGetOrLoadWithoutStaleValueReturnsError(t *testing.T) {
	c := NewWithOptions[string](Options{TTL: time.Minute, StaleFor: time.Minute})
	failure := errors.New("falhou")
	if _, err := c.GetOrLoad("k", func() (string, error) { return "", failure }); !errors.Is(err, failure) {
		t.Fatalf("erro = %v, esperado %v", err, failure)
	}
}

func TestGetOrLoadSharesConcurrentLoads(t *testing.T) {
	c := NewWithOptions[int](Options{TTL: time.Minute})
	const workers = 50
	release := make(chan struct{})
	var calls atomic.Int32

	var started, finished sync.WaitGroup
	started.Add(workers)
	finished.Add(workers)
	for range workers {
		go func() {
			defer finished.Done()
			started.Done()
			got, err := c.GetOrLoad("k", func() (int, error) {
				calls.Add(1)
				<-release
				return 42, nil
			})
			if err != nil || got != 42 {
				t.Errorf("GetOrLoad = (%d, %v), esperado (42, nil)", got, err)
			}
		}()
	}
	started.Wait()
	time.Sleep(20 * time.Millisecond) // dá tempo para os workers ficarem aguardando a carga
	close(release)
	finished.Wait()

	if got := calls.Load(); got != 1 {
		t.Fatalf("load executado %d vezes, esperado 1", got)
	}
}

func TestCacheEvictsOldestBeyondMaxEntries(t *testing.T) {
	c, clock := newClockedCache(Options{MaxEntries: 2})
	c.Set("a", "1")
	*clock = clock.Add(time.Second)
	c.Set("b", "2")
	*clock = clock.Add(time.Second)
	c.Set("c", "3")

	if _, ok := c.Get("a"); ok {
		t.Fatal("entrada mais antiga deveria ter sido removida")
	}
	for _, key := range []string{"b", "c"} {
		if _, ok := c.Get(key); !ok {
			t.Fatalf("entrada %q deveria continuar no cache", key)
		}
	}
}
