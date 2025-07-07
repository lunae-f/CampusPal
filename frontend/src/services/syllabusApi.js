const BASE_URL = '/api/syllabus';

export async function fetchSyllabus({ kougicd, rishunen, crclumcd }) {
  if (!kougicd || !rishunen || !crclumcd) {
    throw new Error('講義コード、履修年度、カリキュラムコードは必須です。');
  }
  const url = `${BASE_URL}/${kougicd}?rishunen=${rishunen}&crclumcd=${crclumcd}`;
  const response = await fetch(url);
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || '情報の取得に失敗しました。');
  }
  return response.json();
}