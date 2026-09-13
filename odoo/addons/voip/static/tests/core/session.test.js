import { describe, expect, test } from "@odoo/hoot";

import { Session } from "@voip/core/session";

describe.current.tags("headless");

test("updates an incoming call based on its SIP cancellation reason", async () => {
    const cases = [
        {
            label: "answered",
            reason: 'SIP;cause=200;text="Call completed elsewhere"',
            actions: ["start", "end"],
        },
        { label: "sip-rejected", reason: "SIP;cause=603", actions: ["reject"] },
        { label: "q850-rejected", reason: "Q.850;cause=21", actions: ["reject"] },
        { label: "missed", reason: "SIP;cause=487", actions: ["miss"] },
    ];

    for (const { label, reason } of cases) {
        const call = {};
        const session = {
            call: call,
            callService: Object.fromEntries(
                ["start", "end", "reject", "miss"].map((action) => [
                    action,
                    async (receivedCall) => {
                        expect(receivedCall).toBe(call);
                        expect.step(`${label}:${action}`);
                    },
                ])
            ),
            isActiveSession: false,
            sipSession: {
                reject({ statusCode }) {
                    expect(statusCode).toBe(487);
                    expect.step(`${label}:sip-reject`);
                },
            },
        };

        await Session.prototype._onIncomingInviteCanceled.call(session, {
            getHeader: () => reason,
        });
    }

    expect.verifySteps([
        "answered:sip-reject",
        "answered:start",
        "answered:end",
        "sip-rejected:sip-reject",
        "sip-rejected:reject",
        "q850-rejected:sip-reject",
        "q850-rejected:reject",
        "missed:sip-reject",
        "missed:miss",
    ]);
});
