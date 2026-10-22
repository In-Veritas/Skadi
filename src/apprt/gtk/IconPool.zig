//! Stable per-window assignments. The original icon belongs to the first
//! window of each run of open windows; remaining windows share a fair pool.
const Pool = @This();
const std = @import("std");

pub const capacity = 100;
pub const Choice = union(enum) { base, variant: usize };

uses: [capacity]usize = @splat(0),
live: usize = 0,

pub fn acquire(self: *Pool, count: usize, random: std.Random) Choice {
    std.debug.assert(count > 0 and count <= capacity);
    defer self.live += 1;
    if (self.live == 0) return .base;

    const least_used = std.mem.min(usize, self.uses[0..count]);
    var available: usize = 0;
    for (self.uses[0..count]) |uses| {
        if (uses == least_used) available += 1;
    }
    // One uniform draw among all eligible variants: neither catalogue order
    // nor visual contrast changes an icon's chance of being selected.
    var rank = random.uintLessThan(usize, available);
    const selected = for (self.uses[0..count], 0..) |uses, index| {
        if (uses != least_used) continue;
        if (rank == 0) break index;
        rank -= 1;
    } else unreachable;
    self.uses[selected] += 1;
    return .{ .variant = selected };
}

pub fn release(self: *Pool, choice: Choice) void {
    std.debug.assert(self.live > 0);
    self.live -= 1;
    switch (choice) {
        .base => {},
        .variant => |index| {
            std.debug.assert(self.uses[index] > 0);
            self.uses[index] -= 1;
        },
    }
}

test "window icons retain identities and reuse only free variants" {
    const t = std.testing;
    var prng = std.Random.DefaultPrng.init(42);
    const random = prng.random();
    var pool: Pool = .{};
    const first = pool.acquire(20, random);
    try t.expect(first == .base);
    var choices: [20]Choice = undefined;
    var seen: [20]bool = @splat(false);
    for (&choices) |*choice| {
        choice.* = pool.acquire(20, random);
        try t.expect(!seen[choice.variant]);
        seen[choice.variant] = true;
    }
    const freed = choices[7].variant;
    pool.release(choices[7]);
    choices[7] = pool.acquire(20, random);
    try t.expectEqual(freed, choices[7].variant);
    pool.release(first);
    const extra = pool.acquire(20, random);
    try t.expect(extra == .variant);
    for (choices) |choice| pool.release(choice);
    pool.release(extra);
    try t.expectEqual(@as(usize, 0), pool.live);
    try t.expect(pool.acquire(20, random) == .base);
}

test "window icons exhaust the pool fairly and survive repeated closes" {
    const t = std.testing;
    var prng = std.Random.DefaultPrng.init(84);
    const random = prng.random();
    var pool: Pool = .{};
    const base = pool.acquire(20, random);
    var choices: [100]Choice = undefined;
    for (&choices, 0..) |*choice, i| {
        choice.* = pool.acquire(20, random);
        if ((i + 1) % 20 == 0) {
            for (pool.uses[0..20]) |uses| try t.expectEqual((i + 1) / 20, uses);
        }
    }
    for (choices) |choice| pool.release(choice);
    pool.release(base);
    try t.expectEqual(@as(usize, 0), pool.live);
}

test "window icons do not always start with the same favorite" {
    var prng = std.Random.DefaultPrng.init(12345);
    var starts: [20]usize = @splat(0);
    for (0..1000) |_| {
        var pool: Pool = .{};
        _ = pool.acquire(20, prng.random());
        starts[pool.acquire(20, prng.random()).variant] += 1;
    }
    // Fixed-seed regression check for a fixed-order or strongly biased draw.
    for (starts) |count| try std.testing.expect(count > 20 and count < 80);
}
