// Long-lived Docxodus worker: one process, many compares.
// Protocol (line-oriented stdin → stdout):
//   COMPARE <basePath> <nextPath> <outPath>
//   → OK <bytes> <ms>
//   → ERR <message>
//   QUIT
//     → BYE
using System.Diagnostics;
using System.Reflection;

var asm = Assembly.LoadFrom(
    Path.Combine(AppContext.BaseDirectory, "Docxodus.dll"));
// Prefer sibling of the published binary if BaseDirectory doesn't have it.
if (asm == null)
{
    Console.Error.WriteLine("FATAL cannot load Docxodus.dll");
    return 1;
}
var t = asm.GetType("Docxodus.Internal.DocxDiffOps")
    ?? throw new Exception("DocxDiffOps missing");
var compare = t.GetMethod("Compare", BindingFlags.Public | BindingFlags.Static)
    ?? throw new Exception("Compare missing");

Console.Out.WriteLine("READY");
Console.Out.Flush();

string? line;
while ((line = Console.In.ReadLine()) != null)
{
    line = line.Trim();
    if (line.Length == 0) continue;
    if (line == "QUIT")
    {
        Console.Out.WriteLine("BYE");
        Console.Out.Flush();
        break;
    }
    if (!line.StartsWith("COMPARE ", StringComparison.Ordinal))
    {
        Console.Out.WriteLine("ERR unknown command");
        Console.Out.Flush();
        continue;
    }
    // Paths may contain spaces — use tab-separated after the verb when possible.
    // Fallback: split on last two spaces from the right for three paths.
    var rest = line.Substring("COMPARE ".Length);
    string basePath, nextPath, outPath;
    if (rest.Contains('\t'))
    {
        var parts = rest.Split('\t');
        if (parts.Length != 3)
        {
            Console.Out.WriteLine("ERR expected 3 tab-separated paths");
            Console.Out.Flush();
            continue;
        }
        basePath = parts[0]; nextPath = parts[1]; outPath = parts[2];
    }
    else
    {
        // three paths separated by spaces, no spaces in paths (our temp files)
        var parts = rest.Split(' ', 3, StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length != 3)
        {
            Console.Out.WriteLine("ERR expected 3 paths");
            Console.Out.Flush();
            continue;
        }
        basePath = parts[0]; nextPath = parts[1]; outPath = parts[2];
    }
    try
    {
        var left = File.ReadAllBytes(basePath);
        var right = File.ReadAllBytes(nextPath);
        var sw = Stopwatch.StartNew();
        var result = (byte[])compare.Invoke(null, new object?[] { left, right, "{}" })!;
        sw.Stop();
        File.WriteAllBytes(outPath, result);
        Console.Out.WriteLine($"OK {result.Length} {sw.Elapsed.TotalMilliseconds:F3}");
        Console.Out.Flush();
    }
    catch (Exception ex)
    {
        var msg = (ex.InnerException ?? ex).Message.Replace('\n', ' ').Replace('\r', ' ');
        Console.Out.WriteLine($"ERR {msg}");
        Console.Out.Flush();
    }
}
return 0;
