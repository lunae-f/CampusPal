/**
 * Syllabus API service
 *
 * このファイルは、バックエンドAPIと通信してシラバス情報を取得するための関数を提供します。
 */

// バックエンドAPIのベースURL
const BASE_URL = '/api/syllabus'

/**
 * 指定された講義コードと履修年度に基づいてシラバス情報を取得します。
 * @param {object} params - パラメータオブジェクト
 * @param {string} params.kougicd - 講義コード
 * @param {string} params.rishunen - 履修年度
 * @returns {Promise<object>} - シラバス情報のJSONオブジェクト
 * @throws {Error} - APIリクエストに失敗した場合、または必須パラメータが不足している場合
 */
export async function fetchSyllabus({ kougicd, rishunen }) {
  // 必須パラメータのバリデーション
  if (!kougicd || !rishunen) {
    throw new Error('講義コード、履修年度は必須です。')
  }

  // APIエンドポイントのURLを構築 (crclumcdを削除)
  const url = `${BASE_URL}/${kougicd}?rishunen=${rishunen}`

  // Fetch APIを使用してGETリクエストを送信
  const response = await fetch(url)

  // レスポンスが正常でない場合（例: 404, 500エラー）
  if (!response.ok) {
    // エラーレスポンスのボディをJSONとして解析
    const errorData = await response.json()
    // エラーメッセージを投げる
    throw new Error(errorData.detail || '情報の取得に失敗しました。')
  }

  // レスポンスボディをJSONとして解析して返す
  return response.json()
}
