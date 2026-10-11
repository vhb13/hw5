"""Run the agent team on tickets: python backend/run_ticket.py 101 [102 103]"""

import asyncio
import sys

from team import mcp_server, run_ticket


async def main(ticket_ids: list[int]) -> None:
    async with mcp_server:  # one MCP server process for the whole run
        for tid in ticket_ids:
            decision = await run_ticket(tid)
            print(decision.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main([int(a) for a in sys.argv[1:]] or [101]))
