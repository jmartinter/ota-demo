from typing import Optional, List

from ota_demo_api.view_model.search_request import SearchRequest
from ota_demo_api.view_model.cluster_search_result import ClusterSearchResult


class SearchRepository:
    def __init__(self, database):
        self.database = database

    async def fetch(self, search_data: SearchRequest) -> Optional[List[ClusterSearchResult]]:
        is_city_country = all([search_data.city, search_data.country])
        if not is_city_country:
            raise ValueError("Required (city, country) filter!")

        query_params = {}
        query = f"""
            SELECT 
                ty_id, 
                trip_type, 
                language, 
                city, 
                latitude,
                longitude, 
                review_count,
                SUM(score) / COUNT(score) AS match_score
            FROM cluster_search
        """

        if is_city_country:
            query +=  """
                WHERE lower(city) = lower(:city) AND lower(country) = lower(:country)
            """
            query_params["city"] = search_data.city
            query_params["country"] = search_data.country

        if search_data.trip_type:
            query += """
                AND trip_type = :trip_type
            """
            query_params["trip_type"] = search_data.trip_type
        else:
            query += """
                AND trip_type = 'all'
            """

        if search_data.language:
            query += """
                AND language = :language
            """
            query_params["language"] = search_data.language
        else:
            query += """
                AND language = 'all'
            """

        if search_data.categories or search_data.hotel_types:
            data_points = []
            data_points += search_data.categories or []
            data_points += search_data.hotel_types or []
            query += """
                AND datapoint = ANY(:data_points)
            """
            query_params["data_points"] = data_points
        else:
            query += """
                AND datapoint = 'oall'
            """

        query += """
            GROUP BY ty_id, trip_type, language, city, latitude, longitude, review_count
            ORDER BY match_score DESC
            LIMIT :limit OFFSET :offset 
        """
        query_params["limit"] = search_data.page_size
        query_params["offset"] = search_data.page_size * search_data.page

        records = await self.database.fetch_all(query, values=query_params)

        if len(records) == 0:
            return None

        results = [ClusterSearchResult(**record) for record in records]

        return results
