from typing import List, Dict

from .schemas import EnsembleResponse, ModelResponse


def _truncate_to_two_lines(text: str) -> str:
	lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
	if not lines:
		return ""
	joined = lines[0]
	if len(lines) > 1:
		joined += " " + lines[1]
	# Limit to ~240 chars to keep it concise
	return joined[:240]


def aggregate_majority(responses: List[ModelResponse]) -> EnsembleResponse:
	votes: Dict[str, int] = {}
	for r in responses:
		votes[r.answer] = votes.get(r.answer, 0) + 1
	# Majority by count
	max_count = max(votes.values()) if votes else 0
	front_runners = [a for a, c in votes.items() if c == max_count]

	if len(front_runners) == 1:
		winning_answer = front_runners[0]
		# Pick the most confident explanation among those who voted for the winning answer
		candidates = [r for r in responses if r.answer == winning_answer]
		best = max(candidates, key=lambda r: r.confidence) if candidates else responses[0]
		expl = _truncate_to_two_lines(best.explanation)
		return EnsembleResponse(
			final_answer=winning_answer,
			explanation=expl,
			votes=votes,
			per_model=responses,
		)

	# Tie-breaker: highest confidence overall among front-runners
	front_responses = [r for r in responses if r.answer in front_runners]
	best = max(front_responses, key=lambda r: r.confidence) if front_responses else responses[0]
	winning_answer = best.answer
	expl = _truncate_to_two_lines(best.explanation)
	return EnsembleResponse(
		final_answer=winning_answer,
		explanation=expl,
		votes=votes,
		per_model=responses,
	)


def aggregate_majority_multi(responses: List[ModelResponse]) -> EnsembleResponse:
	# Treat answers like 'A', 'A+C'; vote per unique combination, then tie-break by confidence
	votes: Dict[str, int] = {}
	for r in responses:
		key = "+".join(sorted(set(str(r.answer).replace(' ', '').split('+')))) or 'A'
		votes[key] = votes.get(key, 0) + 1
	max_count = max(votes.values()) if votes else 0
	front = [k for k, c in votes.items() if c == max_count]
	if len(front) == 1:
		winner = front[0]
		candidates = [r for r in responses if "+".join(sorted(set(str(r.answer).replace(' ', '').split('+')))) == winner]
		best = max(candidates, key=lambda r: r.confidence) if candidates else responses[0]
		expl = _truncate_to_two_lines(best.explanation)
		return EnsembleResponse(final_answer=winner, explanation=expl, votes=votes, per_model=responses)
	# tie by highest confidence among front-runners
	front_resps = [r for r in responses if "+".join(sorted(set(str(r.answer).replace(' ', '').split('+')))) in front]
	best = max(front_resps, key=lambda r: r.confidence) if front_resps else responses[0]
	winner = "+".join(sorted(set(str(best.answer).replace(' ', '').split('+'))))
	expl = _truncate_to_two_lines(best.explanation)
	return EnsembleResponse(final_answer=winner, explanation=expl, votes=votes, per_model=responses)


