#nullable enable

// Copyright (c) Microsoft. All rights reserved.
// Licensed under the MIT license. See LICENSE file in the project root for full license information.

using System.Collections.Generic;

namespace Docxodus.Internal;

/// <summary>
/// Bounded dual-stack ring buffer for undo/redo snapshots. The undo stack holds
/// pre-op snapshots; the redo stack holds post-op snapshots. Recording a new
/// pre-op clears the redo stack (the standard "edit invalidates redo" behavior).
/// Capacity is enforced on the undo side; the redo side mirrors it implicitly
/// because redo entries only exist between an Undo and the next mutation.
/// </summary>
internal sealed class UndoRing<T>
{
    private readonly LinkedList<T> _undo = new();
    private readonly LinkedList<T> _redo = new();
    private readonly int _capacity;

    public UndoRing(int capacity) => _capacity = capacity > 0 ? capacity : 1;

    public int UndoCount => _undo.Count;
    public int RedoCount => _redo.Count;

    /// <summary>Record the document state before applying a new mutation.</summary>
    public void RecordPreOp(T preOpSnapshot)
    {
        _undo.AddLast(preOpSnapshot);
        while (_undo.Count > _capacity) _undo.RemoveFirst();
        _redo.Clear();
    }

    /// <summary>Pop the most recent pre-op snapshot (for an undo).</summary>
    public (T snapshot, bool ok) PopForUndo()
    {
        if (_undo.Count == 0) return (default!, false);
        var v = _undo.Last!.Value;
        _undo.RemoveLast();
        return (v, true);
    }

    /// <summary>Record the document state after applying a mutation we just undid.</summary>
    public void RecordForRedo(T postOpSnapshot) => _redo.AddLast(postOpSnapshot);

    /// <summary>Pop the most recent post-op snapshot (for a redo).</summary>
    public (T snapshot, bool ok) PopForRedo()
    {
        if (_redo.Count == 0) return (default!, false);
        var v = _redo.Last!.Value;
        _redo.RemoveLast();
        return (v, true);
    }

    /// <summary>Push a snapshot back onto the undo stack (used when applying a redo).</summary>
    public void PushBackForUndo(T snapshot) => _undo.AddLast(snapshot);

    public void Clear()
    {
        _undo.Clear();
        _redo.Clear();
    }
}
