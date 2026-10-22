//! Optional Skadi icon catalogue, installed in the user's XDG data directory.
//! GTK owns themed-icon rendering, so theme/scale changes preserve each name.
const WindowIcons = @This();
const std = @import("std");
const glib = @import("glib");
const gdk = @import("gdk");
const gtk = @import("gtk");
const global = @import("../../global.zig");
const Pool = @import("IconPool.zig");

pub const Choice = Pool.Choice;
pub const application_id = "com.mitchellh.ghostty.window";

loaded: bool = false,
names: std.ArrayList([:0]const u8) = .empty,
pool: Pool = .{},

pub fn deinit(self: *WindowIcons, alloc: std.mem.Allocator) void {
    for (self.names.items) |icon| alloc.free(icon);
    self.names.deinit(alloc);
}

pub fn acquire(self: *WindowIcons, alloc: std.mem.Allocator) ?Choice {
    if (!self.loaded) {
        self.loaded = true;
        self.load(alloc) catch |err| {
            std.log.warn("could not load Skadi window icons: {}", .{err});
            self.deinit(alloc);
            self.names = .empty;
        };
    }
    if (self.names.items.len == 0) return null;
    const rng: std.Random.IoSource = .{ .io = global.io() };
    return self.pool.acquire(self.names.items.len, rng.interface());
}

pub fn release(self: *WindowIcons, choice: Choice) void {
    self.pool.release(choice);
}

pub fn name(self: *const WindowIcons, choice: Choice) ?[:0]const u8 {
    return switch (choice) {
        .base => null,
        .variant => |index| self.names.items[index],
    };
}

fn load(self: *WindowIcons, alloc: std.mem.Allocator) !void {
    const data = std.mem.span(glib.getUserDataDir());
    const desktop = try std.fmt.allocPrintSentinel(alloc, "{s}/applications/{s}.desktop", .{ data, application_id }, 0);
    defer alloc.free(desktop);
    if (glib.fileTest(desktop, .{ .is_regular = true }) == 0) return;
    const path = try std.fmt.allocPrintSentinel(alloc, "{s}/skadi/window-icons/icons.txt", .{data}, 0);
    defer alloc.free(path);
    var contents: [*]u8 = undefined;
    var length: usize = 0;
    if (glib.fileGetContents(path, &contents, &length, null) == 0) return;
    defer glib.free(contents);

    const display = gdk.Display.getDefault() orelse return;
    const theme = gtk.IconTheme.getForDisplay(display);
    var lines = std.mem.tokenizeAny(u8, contents[0..length], "\r\n");
    while (lines.next()) |line| {
        if (self.names.items.len == Pool.capacity) break;
        if (!std.mem.startsWith(u8, line, "skadi-fluke-") or line.len > 128) continue;
        if (std.mem.findScalar(u8, line, 0) != null) continue;
        const icon = try alloc.dupeZ(u8, line);
        errdefer alloc.free(icon);
        if (theme.hasIcon(icon) == 0) {
            alloc.free(icon);
            continue;
        }
        try self.names.append(alloc, icon);
    }
}
