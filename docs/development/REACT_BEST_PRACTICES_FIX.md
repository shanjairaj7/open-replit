# React Best Practices and State Management Guidelines

## Problem Statement
The current system prompt over-emphasizes Zustand usage and lacks proper React best practices guidance, leading to infinite loops and anti-patterns in useEffect hooks.

## Proposed Changes to simpler_prompt.py

### 1. **Add after line 867 (after Zustand mention)**:

```
- **State Management Hierarchy**: Use the simplest solution that meets your needs:
  1. **useState**: For local component state that doesn't need to be shared
  2. **Zustand**: For global state that needs to be accessed across many components
  3. **React Query/TanStack Query**: For server state (API data, caching, synchronization)
  
  Important: NOT all state needs to be in Zustand. Use useState for:
  - Form inputs and local UI state
  - Temporary data that doesn't affect other components
  - Derived state that can be computed from props
```

### 2. **Add after line 908 (after data handling section)**:

```
- **useEffect Best Practices**: To prevent infinite loops:
  1. **Minimal Dependencies**: Only include values that actually trigger re-runs
  2. **Avoid Object Dependencies**: Use primitive values or memoized callbacks
  3. **Condition Updates**: Check if values actually changed before updating state
  4. **Two-Way Binding Anti-Pattern**: Don't automatically sync every Zustand store change to local state
  
  Example pattern:
  ```tsx
  // Bad - creates infinite loop
  useEffect(() => {
    setLocalState(store.someValue);
  }, [store.someValue]); // Changes every render
  
  // Good - only update when actually different
  useEffect(() => {
    if (localState !== store.someValue) {
      setLocalState(store.someValue);
    }
  }, [store.someValue, localState]);
  
  // Better - use store value directly or derive state
  const displayValue = store.someValue;
  ```

- **Server State Management**: For API data, consider using React Query instead of Zustand:
  - Automatic caching, refetching, and stale-while-revalidate
  - Built-in loading/error states
  - No manual synchronization needed
  - Better performance with deduped requests
```

### 3. **Modify line 867 to soften Zustand emphasis**:

Change from:
```
- Frontend is vitejs app with shadcn/ui for building user interface using Zustand for state management...
```

To:
```
- Frontend is vitejs app with shadcn/ui for building user interface using Zustand for global state management when needed, useState for local component state, and consider React Query for server state...
```

## Implementation Strategy

1. **Update simpler_prompt.py** with the above changes
2. **Clear project pool** to ensure new projects use updated prompt
3. **Monitor future generations** for improved patterns
4. **Consider adding React Query** to boilerplate as an alternative to Zustand for API state

## Expected Benefits

1. **Reduced infinite loops** from better useEffect patterns
2. **More appropriate state management** based on use case
3. **Better performance** from avoiding unnecessary re-renders
4. **Cleaner code** with separation of concerns (local vs global vs server state)

## Additional Recommendations

1. **Add React Query to boilerplate** as an alternative for API state management
2. **Create examples** showing when to use each state management approach
3. **Add linting rules** to catch common anti-patterns
4. **Provide code snippets** for common patterns in the prompt