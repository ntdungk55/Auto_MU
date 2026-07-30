Add-Type -AssemblyName System.Drawing

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class WinApi {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);

    [DllImport("user32.dll", SetLastError=true)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);

    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }
}
'@

$hwnd = [WinApi]::GetForegroundWindow()
if ($hwnd -eq [IntPtr]::Zero) {
    Write-Host "No focused window."
    exit 1
}

$titleBuilder = New-Object System.Text.StringBuilder 512
[void][WinApi]::GetWindowText($hwnd, $titleBuilder, $titleBuilder.Capacity)
$title = $titleBuilder.ToString()

$rect = New-Object WinApi+RECT
if (-not [WinApi]::GetWindowRect($hwnd, [ref]$rect)) {
    Write-Host "Cannot get focused window rect."
    exit 1
}

$desktop = [Environment]::GetFolderPath("Desktop")
$outDir = Join-Path $desktop ("focused_window_captures_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

Write-Host "Focused window: $title"
Write-Host "Handle: $hwnd"
Write-Host "Output: $outDir"
Write-Host "Capturing 60 images, 1 image per second. Close this window or press Ctrl+C to stop."

for ($i = 1; $i -le 60; $i++) {
    [void][WinApi]::GetWindowRect($hwnd, [ref]$rect)
    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top

    if ($width -le 0 -or $height -le 0) {
        Write-Host ("{0}/60 skip invalid size {1}x{2}" -f $i, $width, $height)
        Start-Sleep -Seconds 1
        continue
    }

    $bmp = New-Object System.Drawing.Bitmap $width, $height
    $gfx = [System.Drawing.Graphics]::FromImage($bmp)
    try {
        $gfx.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bmp.Size)
        $file = Join-Path $outDir ("capture_{0:D3}_{1}.png" -f $i, (Get-Date -Format "yyyyMMdd_HHmmss_fff"))
        $bmp.Save($file, [System.Drawing.Imaging.ImageFormat]::Png)
        Write-Host ("{0}/60 saved {1}" -f $i, (Split-Path $file -Leaf))
    } finally {
        $gfx.Dispose()
        $bmp.Dispose()
    }

    if ($i -lt 60) {
        Start-Sleep -Seconds 1
    }
}

Write-Host "Done. Output: $outDir"
