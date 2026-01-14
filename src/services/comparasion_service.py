from src.models.respostas_lake import RespostasLake
from src.services.damerau_levenshtein_service import DamerauLevenshteinService
from src.services.jaccard_service import JaccardService


class ComparisonService:
    # pylint: disable=no-method-argument,redefined-outer-name,reimported,import-outside-toplevel
    @staticmethod
    def init_worker():
        from src import app, db
        app.app_context().push()
        db.engine.dispose()

    # pylint: enable=no-method-argument,redefined-outer-name,reimported,import-outside-toplevel
    @staticmethod
    def compare(contest, contest_to_be_compared, comparasionFunction):
        user1_dict = {item['item_id']: item['resposta_usuario'] for item in contest}
        user2_dict = {item['item_id']: item['resposta_usuario'] for item in contest_to_be_compared}

        all_items = set(user1_dict.keys()) | set(user2_dict.keys())

        user1_responses = set()
        user2_responses = set()
        for item_id in all_items:
            resp1 = user1_dict.get(item_id, None)
            user1_responses.add((item_id, resp1))

            resp2 = user2_dict.get(item_id, None)
            user2_responses.add((item_id, resp2))

        return comparasionFunction(user1_responses, user2_responses)

    @staticmethod
    def process_user_batch(user_batch, all_users, exam_id=None, metrics='both'):

        batch_results = []

        for user in user_batch:
            current_user_response = RespostasLake.select_user_questions(user, exam_id)
            for other_user in all_users:
                if other_user == user:
                    continue

                respostas_other_user = RespostasLake.select_user_questions(other_user, exam_id)
                jaccard_result = None
                dl_result = None

                if metrics in ['jaccard', 'both']:
                    jaccard_result = ComparisonService.compare(current_user_response,
                                                                respostas_other_user,
                                                                JaccardService.jaccard_index)

                if metrics in ['dl', 'both']:
                    dl_result = ComparisonService.compare(current_user_response,
                                                                respostas_other_user,
                                                                DamerauLevenshteinService.damerau_levenshtein_similarity)

                should_append = False
                if metrics == 'jaccard' and jaccard_result and jaccard_result > 0.01:
                    should_append = True
                elif metrics == 'dl' and dl_result and dl_result > 0.01:
                    should_append = True
                elif metrics == 'both' and jaccard_result and jaccard_result > 0.01:
                    should_append = True

                if should_append:
                    result = {
                        'user': user,
                        'compared_with': other_user,
                        'response_other': respostas_other_user,
                        'user_resp': current_user_response
                    }

                    if jaccard_result is not None:
                        result['jaccard_index'] = jaccard_result
                    if dl_result is not None:
                        result['dl_similarity'] = dl_result

                    batch_results.append(result)

        return batch_results