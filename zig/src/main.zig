const std = @import("std");

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    try stdout.print("Hello\n " , .{});
    var score: i32 = 20;
    try stdout.print("run...\n" ,.{});
    score +=45 ;
    try stdout.print("New score :{}" , .{score});
}