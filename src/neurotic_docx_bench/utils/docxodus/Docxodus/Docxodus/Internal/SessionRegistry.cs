#nullable enable

using System;
using System.Collections.Concurrent;
using System.Threading;

namespace Docxodus.Internal;

/// <summary>
/// Process-wide pool of <see cref="DocxSession"/> instances keyed by an integer handle.
/// Shared between the WASM JSExport bridge (<c>DocxSessionBridge</c>) and the stdio
/// NDJSON host (<c>docxodus-pyhost</c>) so both transports speak the same handle protocol.
/// Sessions live until <see cref="CloseSession"/> is called or the host process exits.
/// </summary>
internal static class SessionRegistry
{
    private static readonly ConcurrentDictionary<int, DocxSession> _sessions = new();
    private static int _nextId;

    public static int OpenSession(byte[] bytes, DocxSessionSettings? settings)
    {
        var session = new DocxSession(bytes, settings);
        var id = Interlocked.Increment(ref _nextId);
        _sessions[id] = session;
        return id;
    }

    public static void CloseSession(int handle)
    {
        if (_sessions.TryRemove(handle, out var s)) s.Dispose();
    }

    public static DocxSession Get(int handle)
    {
        if (!_sessions.TryGetValue(handle, out var s))
            throw new ArgumentException($"unknown session handle: {handle}");
        return s;
    }

    public static int Count => _sessions.Count;

    public static void DisposeAll()
    {
        foreach (var kv in _sessions)
        {
            if (_sessions.TryRemove(kv.Key, out var s)) s.Dispose();
        }
    }
}
