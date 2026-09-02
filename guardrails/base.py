from typing import Dict, Any, Tuple

class Guardrail:
	name = "base"

	async def check(self, context: Dict[str, Any]) -> Dict[str, Any]:
		return context


class UtilityWorker:

	@staticmethod
	async def load_policies(context: Dict) -> Dict:
		"""
		This function will extract policies from given context
		"""
		return context.get("policies", {})


	@staticmethod
	async def load_global_policies(context: Dict) -> Dict:
		"""
		An async static method that reurns the global policies.
		"""
		policies = await UtilityWorker.load_policies(context=context)
		return policies.get("global_policies", {})


	@staticmethod
	async def load_application_policies(context: Dict) -> Dict:
		"""
		An async static method that reurns the global policies.
		"""
		application_id = context.get("app_id", None)
		if application_id:
			policies = await UtilityWorker.load_policies(context=context)
			return policies.get("application_policies", {}).get(application_id)
		return None


	@staticmethod
	async def load_pattern(pattern: Dict) -> Dict:
		"""
		This function format the patterns and will return as required by the pii masking.
		"""
		return [
			{
				"label": value[0],
				"value": value[1]
			}
			for value in pattern.values()
		]

	@staticmethod
	async def check_masking_required(context: Dict) -> Tuple:
		"""
		This function will check the policy has masking rules or not for this application with the patterns of masking.
		Global policy is checked first. If the application policy does not mention pii_masking at all, the global
		decision is inherited as-is. If the application policy explicitly sets pii_masking, that value wins - False
		disables masking outright, True keeps it enabled and uses the application's own patterns if it defines any,
		otherwise it falls back to the global patterns.
		"""

		global_policies = await UtilityWorker.load_global_policies(context=context)
		pii_masking = global_policies.get("pii_masking", False)
		pii_masking_pattern = []
		if pii_masking:
			pii_masking_pattern = await UtilityWorker.load_pattern(global_policies.get("patterns", {}))

		application_policies = await UtilityWorker.load_application_policies(context=context)
		if application_policies and "pii_masking" in application_policies:
			application_pii_masking = application_policies["pii_masking"]

			if application_pii_masking is False:
				pii_masking = False
				pii_masking_pattern = []
			else:
				pii_masking = application_pii_masking
				application_pii_masking_pattern = await UtilityWorker.load_pattern(application_policies.get("patterns", {}))
				if application_pii_masking_pattern:
					pii_masking_pattern = application_pii_masking_pattern

		return pii_masking, pii_masking_pattern

	@staticmethod
	async def check_injection_required(context: Dict) -> bool:
		"""
		This function will check whether prompt-injection detection is required for this application.
		Global policy is checked first. If the application policy does not mention prompt_injection at all, the
		global decision is inherited as-is. If the application policy explicitly sets prompt_injection, that value
		overrides the global one.
		"""

		global_policies = await UtilityWorker.load_global_policies(context=context)
		prompt_injection = global_policies.get("prompt_injection", False)

		application_policies = await UtilityWorker.load_application_policies(context=context)
		if application_policies and "prompt_injection" in application_policies:
			prompt_injection = application_policies["prompt_injection"]

		return prompt_injection

	@staticmethod
	async def check_block_topics(context: Dict) -> list:
		"""
		This function resolves the list of blocked topics for this application.
		Global policy is checked first. If the application policy does not mention block_topics at all, the
		global list is inherited as-is. If the application policy explicitly defines block_topics, that list
		overrides the global one entirely.
		"""

		global_policies = await UtilityWorker.load_global_policies(context=context)
		block_topics = global_policies.get("block_topics", [])

		application_policies = await UtilityWorker.load_application_policies(context=context)
		if application_policies and "block_topics" in application_policies:
			block_topics = application_policies["block_topics"]

		return block_topics
