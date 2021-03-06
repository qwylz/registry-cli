import unittest
from registry import Registry, Requests, get_tags, parse_args, delete_tags, delete_tags_by_age
from mock import MagicMock, patch
import requests


class ReturnValue:

    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


class MockRequests:

    def __init__(self, return_value=ReturnValue()):
        self.return_value = return_value
        self.request = MagicMock(return_value=self.return_value)

    def reset_return_value(self, status_code=200, text=""):
        self.return_value.status_code = status_code
        self.return_value.text = text


class TestRequestsClass(unittest.TestCase):

    def test_requests_created(self):
        # simply create requests class and make sure it raises an exception
        # from requests module
        # this test will fail if port 45272 is open on local machine
        # is so, either change port below or check what is this service you are
        # running on port 45272
        with self.assertRaises(requests.exceptions.ConnectionError):
            Requests().request("GET", "http://localhost:45272")


class TestCreateMethod(unittest.TestCase):

    def test_create_nologin(self):
        r = Registry.create("testhost", None, False)
        self.assertTrue(isinstance(r.http, Requests))
        self.assertEqual(r.hostname, "testhost")
        self.assertEqual(r.no_validate_ssl, False)

    def test_create_login(self):
        r = Registry.create("testhost2", "testlogin:testpass", False)
        self.assertEqual(r.hostname, "testhost2")
        self.assertTrue(isinstance(r.http, Requests))
        self.assertEqual(r.username, "testlogin")
        self.assertEqual(r.password, "testpass")

    def test_validate_ssl(self):
        r = Registry.create("testhost3", None, True)
        self.assertTrue(isinstance(r.http, Requests))
        self.assertTrue(r.no_validate_ssl)
        self.assertEqual(r.username, None)
        self.assertEqual(r.password, None)

    def test_invalid_login(self):
        with self.assertRaises(SystemExit):
            Registry.create("testhost4", "invalid_login", False)


class TestParseLogin(unittest.TestCase):

    def setUp(self):
        self.registry = Registry()

    def test_login_args_ok(self):
        (username, password) = self.registry.parse_login("username:password")
        self.assertEqual(username, "username")
        self.assertEqual(password, "password")
        self.assertEqual(self.registry.last_error, None)

    def test_login_args_double_colon(self):
        (username, password) = self.registry.parse_login("username:pass:word")
        self.assertEqual(username, "username")
        self.assertEqual(password, "pass:word")
        self.assertEqual(self.registry.last_error, None)

    # this test becomes reduntant
    def test_login_args_no_colon(self):
        (username, password) = self.registry.parse_login("username/password")
        self.assertEqual(username, None)
        self.assertEqual(password, None)
        self.assertEqual(self.registry.last_error,
                         "Please provide -l in the form USER:PASSWORD")

    def test_login_args_singlequoted(self):
        (username, password) = self.registry.parse_login("'username':password")
        self.assertEqual(username, 'username')
        self.assertEqual(password, "password")
        self.assertEqual(self.registry.last_error, None)

    def test_login_args_doublequoted(self):
        (username, password) = self.registry.parse_login('"username":"password"')
        self.assertEqual(username, 'username')
        self.assertEqual(password, "password")
        self.assertEqual(self.registry.last_error, None)

    def test_login_colon_username(self):
        """
        this is to test that if username contains colon,
        then the result will be invalid in this case
        and no error will be printed
        """
        (username, password) = self.registry.parse_login(
            "'user:name':'pass:word'")
        self.assertEqual(username, 'user')
        self.assertEqual(password, "name':'pass:word")


class TestRegistrySend(unittest.TestCase):

    def setUp(self):
        self.registry = Registry()
        self.registry.http = MockRequests()
        self.registry.hostname = "http://testdomain.com"

    def test_get_ok(self):
        self.registry.http.reset_return_value(200)
        response = self.registry.send('/test_string')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.registry.last_error, None)
        self.registry.http.request.assert_called_with('GET',
                                                      'http://testdomain.com/test_string',
                                                      auth=(None, None),
                                                      headers=self.registry.HEADERS,
                                                      verify=True)

    def test_invalid_status_code(self):
        self.registry.http.reset_return_value(400)
        response = self.registry.send('/v2/catalog')
        self.assertEqual(response, None)
        self.assertEqual(self.registry.last_error, 400)

    def test_login_pass(self):
        self.registry.username = "test_login"
        self.registry.password = "test_password"
        self.registry.http.reset_return_value(200)
        response = self.registry.send('/v2/catalog')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.registry.last_error, None)
        self.registry.http.request.assert_called_with('GET',
                                                      'http://testdomain.com/v2/catalog',
                                                      auth=("test_login",
                                                            "test_password"),
                                                      headers=self.registry.HEADERS,
                                                      verify=True)


class TestListImages(unittest.TestCase):

    def setUp(self):
        self.registry = Registry()
        self.registry.http = MockRequests()
        self.registry.hostname = "http://testdomain.com"

    def test_list_images_ok(self):
        self.registry.http.reset_return_value(status_code=200,
                                              text='{"repositories":["image1","image2"]}')
        response = self.registry.list_images()
        self.assertEqual(response, ["image1", "image2"])
        self.assertEqual(self.registry.last_error, None)

    def test_list_images_invalid_http_response(self):
        self.registry.http.reset_return_value(404)
        response = self.registry.list_images()
        self.assertEqual(response, [])
        self.assertEqual(self.registry.last_error, 404)


class TestListTags(unittest.TestCase):

    def setUp(self):
        self.registry = Registry()
        self.registry.http = MockRequests()
        self.registry.hostname = "http://testdomain.com"
        self.registry.http.reset_return_value(200)

    def test_list_one_tag_ok(self):
        self.registry.http.reset_return_value(status_code=200,
                                              text=u'{"name":"image1","tags":["0.1.306"]}')

        response = self.registry.list_tags('image1')
        self.assertEqual(response, ["0.1.306"])
        self.assertEqual(self.registry.last_error, None)

    def test_list_tags_invalid_http_response(self):
        self.registry.http.reset_return_value(status_code=400,
                                              text="")

        response = self.registry.list_tags('image1')
        self.assertEqual(response, [])
        self.assertEqual(self.registry.last_error, 400)

    def test_list_tags_invalid_json(self):
        self.registry.http.reset_return_value(status_code=200,
                                              text="invalid_json")

        response = self.registry.list_tags('image1')
        self.assertEqual(response, [])
        self.assertEqual(self.registry.last_error,
                         "list_tags: invalid json response")

    def test_list_one_tag_sorted(self):
        self.registry.http.reset_return_value(status_code=200,
                                              text=u'{"name":"image1","tags":["0.1.306", "0.1.300", "0.1.290"]}')

        response = self.registry.list_tags('image1')
        self.assertEqual(response, ["0.1.290", "0.1.300", "0.1.306"])
        self.assertEqual(self.registry.last_error, None)

    def test_list_tags_like_various(self):
        tags_list = set(['FINAL_0.1', 'SNAPSHOT_0.1',
                         "0.1.SNAP", "1.0.0_FINAL"])
        self.assertEqual(get_tags(tags_list, "", set(
            ["FINAL"])), set(["FINAL_0.1", "1.0.0_FINAL"]))
        self.assertEqual(get_tags(tags_list, "", set(
            ["SNAPSHOT"])), set(['SNAPSHOT_0.1']))
        self.assertEqual(get_tags(tags_list, "", set()),
                         set(['FINAL_0.1', 'SNAPSHOT_0.1', "0.1.SNAP", "1.0.0_FINAL"]))
        self.assertEqual(get_tags(tags_list, "", set(["ABSENT"])), set())

        self.assertEqual(
            get_tags(tags_list, "IMAGE:TAG00", ""), set(["TAG00"]))
        self.assertEqual(get_tags(tags_list, "IMAGE:TAG00", set(
            ["WILL_NOT_BE_CONSIDERED"])), set(["TAG00"]))


class TestListDigest(unittest.TestCase):

    def setUp(self):
        self.registry = Registry()
        self.registry.http = MockRequests()
        self.registry.hostname = "http://testdomain.com"
        self.registry.http.reset_return_value(200)

    def test_get_digest_ok(self):
        self.registry.http.reset_return_value(status_code=200,
                                              text=('{'
                                                    '"schemaVersion": 2,\n '
                                                    '"mediaType": "application/vnd.docker.distribution.manifest.v2+json"'
                                                    '"digest": "sha256:357ea8c3d80bc25792e010facfc98aee5972ebc47e290eb0d5aea3671a901cab"'
                                                    ))

        self.registry.http.return_value.headers = {
            'Content-Length': '4935',
            'Docker-Content-Digest': 'sha256:85295b0e7456a8fbbc886722b483f87f2bff553fa0beeaf37f5d807aff7c1e52',
            'X-Content-Type-Options': 'nosniff'
        }

        response = self.registry.get_tag_digest('image1', '0.1.300')
        self.registry.http.request.assert_called_with(
            "HEAD",
            "http://testdomain.com/v2/image1/manifests/0.1.300",
            auth=(None, None),
            headers=self.registry.HEADERS,
            verify=True
        )

        self.assertEqual(
            response, 'sha256:85295b0e7456a8fbbc886722b483f87f2bff553fa0beeaf37f5d807aff7c1e52')
        self.assertEqual(self.registry.last_error, None)

    def test_invalid_status_code(self):
        self.registry.http.reset_return_value(400)
        response = self.registry.get_tag_digest('image1', '0.1.300')
        self.assertEqual(response, None)

    def test_invalid_headers(self):
        self.registry.http.reset_return_value(200, "invalid json")
        self.registry.http.return_value.headers = "invalid headers"
        with self.assertRaises(TypeError):
            self.registry.get_tag_digest('image1', '0.1.300')


class TestTagConfig(unittest.TestCase):

    def setUp(self):
        self.registry = Registry()
        self.registry.http = MockRequests()
        self.registry.hostname = "http://testdomain.com"
        self.registry.http.reset_return_value(200)

    def test_get_tag_config_ok(self):
        self.registry.http.reset_return_value(
            200,
            '''
                {
                  "schemaVersion": 2,
                  "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
                  "config": {
                    "mediaType": "application/vnd.docker.container.image.v1+json",
                    "size": 12953,
                    "digest": "sha256:8d71dfbf239c0015ad66993d55d3954cee2d52d86f829fdff9ccfb9f23b75aa8"
                  },
                  "layers": [
                    {
                      "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                      "size": 51480140,
                      "digest": "sha256:c6b13209f43b945816b7658a567720983ac5037e3805a779d5772c61599b4f73"
                    }
                   ]
                }
            '''
        )

        response = self.registry.get_tag_config('image1', '0.1.300')

        self.registry.http.request.assert_called_with(
            "GET",
            "http://testdomain.com/v2/image1/manifests/0.1.300",
            auth=(None, None),
            headers=self.registry.HEADERS,
            verify=True)

        self.assertEqual(
            response, {'mediaType': 'application/vnd.docker.container.image.v1+json', 'size': 12953, 'digest': 'sha256:8d71dfbf239c0015ad66993d55d3954cee2d52d86f829fdff9ccfb9f23b75aa8'})
        self.assertEqual(self.registry.last_error, None)

    def test_tag_config_scheme_v1(self):
        with self.assertRaises(SystemExit):
            self.registry.http.reset_return_value(
                200,
                '''
                {
                  "schemaVersion": 1
                }
            '''
            )
            response = self.registry.get_tag_config('image1', '0.1.300')

    def test_invalid_status_code(self):
        self.registry.http.reset_return_value(400, "whatever")

        response = self.registry.get_tag_config('image1', '0.1.300')

        self.registry.http.request.assert_called_with(
            "GET",
            "http://testdomain.com/v2/image1/manifests/0.1.300",
            auth=(None, None),
            headers=self.registry.HEADERS,
            verify=True
        )

        self.assertEqual(response, [])
        self.assertEqual(self.registry.last_error, 400)


class TestImageAge(unittest.TestCase):

    def setUp(self):
        self.registry = Registry()
        self.registry.http = MockRequests()
        self.registry.hostname = "http://testdomain.com"
        self.registry.http.reset_return_value(200)

    def test_image_age_ok(self):
        self.registry.http.reset_return_value(
            200,
            '''
                {
                  "architecture": "amd64",
                  "author": "Test",
                  "config": {},
                  "container": "c467822c5981cd446068eebafd81cb5cde60d4341a945f3fbf67e456dde5af51",
                  "container_config": {},
                  "created": "2017-12-27T12:47:33.511765448Z",
                  "docker_version": "1.11.2",
                  "history": []
                }
            '''
        )
        json_payload = {'mediaType': 'application/vnd.docker.container.image.v1+json', 'size': 12953,
                        'digest': 'sha256:8d71dfbf239c0015ad66993d55d3954cee2d52d86f829fdff9ccfb9f23b75aa8'}
        header = {"Accept": "{0}".format(json_payload['mediaType'])}
        response = self.registry.get_image_age('image1', json_payload)

        self.registry.http.request.assert_called_with(
            "GET",
            "http://testdomain.com/v2/image1/blobs/sha256:8d71dfbf239c0015ad66993d55d3954cee2d52d86f829fdff9ccfb9f23b75aa8",
            auth=(None, None),
            headers=header,
            verify=True)

        self.assertEqual(
            response, "2017-12-27T12:47:33.511765448Z")
        self.assertEqual(self.registry.last_error, None)

    def test_image_age_nok(self):
        self.registry.http.reset_return_value(400, "err")
        json_payload = {'mediaType': 'application/vnd.docker.container.image.v1+json', 'size': 12953,
                        'digest': 'sha256:8d71dfbf239c0015ad66993d55d3954cee2d52d86f829fdff9ccfb9f23b75aa8'}
        header = {"Accept": "{0}".format(json_payload['mediaType'])}
        response = self.registry.get_image_age('image1', json_payload)

        self.registry.http.request.assert_called_with(
            "GET",
            "http://testdomain.com/v2/image1/blobs/sha256:8d71dfbf239c0015ad66993d55d3954cee2d52d86f829fdff9ccfb9f23b75aa8",
            auth=(None, None),
            headers=header,
            verify=True)

        self.assertEqual(response, [])
        self.assertEqual(self.registry.last_error, 400)


class TestListLayers(unittest.TestCase):

    def setUp(self):
        self.registry = Registry()
        self.registry.http = MockRequests()
        self.registry.hostname = "http://testdomain.com"
        self.registry.http.reset_return_value(200)

    def test_list_layers_schema_version_2_ok(self):
        self.registry.http.reset_return_value(
            200,
            '''
            {
                "schemaVersion": 2,
                "layers": "layers_list"
            }
            '''
        )

        response = self.registry.list_tag_layers('image1', '0.1.300')

        self.registry.http.request.assert_called_with(
            "GET",
            "http://testdomain.com/v2/image1/manifests/0.1.300",
            auth=(None, None),
            headers=self.registry.HEADERS,
            verify=True
        )

        self.assertEqual(response, "layers_list")
        self.assertEqual(self.registry.last_error, None)

    def test_list_layers_schema_version_1_ok(self):
        self.registry.http.reset_return_value(
            200,
            '''
            {
                "schemaVersion": 1,
                "fsLayers": "layers_list"
            }
            '''
        )

        response = self.registry.list_tag_layers('image1', '0.1.300')

        self.registry.http.request.assert_called_with(
            "GET",
            "http://testdomain.com/v2/image1/manifests/0.1.300",
            auth=(None, None),
            headers=self.registry.HEADERS,
            verify=True
        )

        self.assertEqual(response, "layers_list")
        self.assertEqual(self.registry.last_error, None)

    def test_list_layers_invalid_status_code(self):
        self.registry.http.reset_return_value(400, "whatever")

        response = self.registry.list_tag_layers('image1', '0.1.300')

        self.registry.http.request.assert_called_with(
            "GET",
            "http://testdomain.com/v2/image1/manifests/0.1.300",
            auth=(None, None),
            headers=self.registry.HEADERS,
            verify=True
        )

        self.assertEqual(response, [])
        self.assertEqual(self.registry.last_error, 400)


class TestDeletion(unittest.TestCase):

    def setUp(self):
        self.registry = Registry()
        self.registry.http = MockRequests()
        self.registry.hostname = "http://testdomain.com"
        self.registry.http.reset_return_value(200, "MOCK_DIGEST")
        self.registry.http.return_value.headers = {
            'Content-Length': '4935',
            'Docker-Content-Digest': 'MOCK_DIGEST_HEADER',
            'X-Content-Type-Options': 'nosniff'
        }

    def test_delete_tag_dry_run(self):
        response = self.registry.delete_tag("image1", 'test_tag', True, [])
        self.assertFalse(response)

    def test_delete_tag_ok(self):
        keep_tag_digests = ['DIGEST1', 'DIGEST2']
        response = self.registry.delete_tag(
            'image1', 'test_tag', False, keep_tag_digests)
        self.assertEqual(response, True)
        self.assertEqual(self.registry.http.request.call_count, 2)
        self.registry.http.request.assert_called_with(
            "DELETE",
            "http://testdomain.com/v2/image1/manifests/MOCK_DIGEST_HEADER",
            auth=(None, None),
            headers=self.registry.HEADERS,
            verify=True
        )
        self.assertTrue("MOCK_DIGEST_HEADER" in keep_tag_digests)

    def test_delete_tag_ignored(self):
        response = self.registry.delete_tag(
            'image1', 'test_tag', False, ['MOCK_DIGEST_HEADER'])
        self.assertEqual(response, True)
        self.assertEqual(self.registry.http.request.call_count, 1)
        self.registry.http.request.assert_called_with(
            "HEAD",
            "http://testdomain.com/v2/image1/manifests/test_tag",
            auth=(None, None),
            headers=self.registry.HEADERS,
            verify=True
        )

    def test_delete_tag_no_digest(self):
        self.registry.http.reset_return_value(400, "")
        response = self.registry.delete_tag('image1', 'test_tag', False, [])
        self.assertFalse(response)
        self.assertEqual(self.registry.last_error, 400)


class TestDeleteTagsFunction(unittest.TestCase):

    def setUp(self):
        self.registry = Registry()
        self.delete_mock = MagicMock()
        self.registry.delete_tag = self.delete_mock
        self.registry.http = MockRequests()
        self.registry.hostname = "http://testdomain.com"
        self.registry.http.reset_return_value(200, "MOCK_DIGEST")
        self.registry.http.return_value.headers = {
            'Content-Length': '4935',
            'Docker-Content-Digest': 'MOCK_DIGEST_HEADER',
            'X-Content-Type-Options': 'nosniff'
        }

    def test_delete_tags_no_keep(self):
        delete_tags(self.registry, "imagename", False, ["tag_to_delete"], [])
        self.delete_mock.assert_called_with(
            "imagename",
            "tag_to_delete",
            False,
            []
        )

    def test_delete_tags_keep(self):
        digest_mock = MagicMock(return_value="DIGEST_MOCK")
        self.registry.get_tag_digest = digest_mock

        delete_tags(self.registry, "imagename",
                    False, ["tag1", "tag2"], ["tag2"])

        digest_mock.assert_called_with("imagename", "tag2")

        self.delete_mock.assert_called_with(
            "imagename",
            "tag1",
            False,
            ['DIGEST_MOCK']
        )

    def test_delete_tags_digest_none(self):
        digest_mock = MagicMock(return_value=None)
        self.registry.get_tag_digest = digest_mock
        delete_tags(self.registry, "imagename",
                    False, ["tag1", "tag2"], ["tag2"])

        digest_mock.assert_called_with("imagename", "tag2")

        self.delete_mock.assert_called_with(
            "imagename",
            "tag1",
            False,
            []
        )


class TestDeleteTagsByAge(unittest.TestCase):

    def setUp(self):
        self.registry = Registry()
        self.registry.http = MockRequests()

        self.get_tag_config_mock = MagicMock(return_value={'mediaType': 'application/vnd.docker.container.image.v1+json', 'size': 12953,
                                                           'digest': 'sha256:8d71dfbf239c0015ad66993d55d3954cee2d52d86f829fdff9ccfb9f23b75aa8'})
        self.registry.get_tag_config = self.get_tag_config_mock
        self.get_image_age_mock = MagicMock(
            return_value="2017-12-27T12:47:33.511765448Z")
        self.registry.get_image_age = self.get_image_age_mock
        self.list_tags_mock = MagicMock(return_value=["image"])
        self.registry.list_tags = self.list_tags_mock
        self.get_tag_digest_mock = MagicMock()
        self.registry.get_tag_digest = self.get_tag_digest_mock
        self.registry.http = MockRequests()
        self.registry.hostname = "http://testdomain.com"
        self.registry.http.reset_return_value(200, "MOCK_DIGEST")

    @patch('registry.delete_tags')
    def test_delete_tags_by_age_no_keep(self, delete_tags_patched):
        delete_tags_by_age(self.registry, "imagename", False, 24, [])
        self.list_tags_mock.assert_called_with(
            "imagename"
        )
        self.list_tags_mock.assert_called_with("imagename")
        self.get_tag_config_mock.assert_called_with("imagename", "image")
        delete_tags_patched.assert_called_with(
            self.registry, "imagename", False, ["image"], [])

    @patch('registry.delete_tags')
    def test_delete_tags_by_age_keep_tags(self, delete_tags_patched):
        delete_tags_by_age(self.registry, "imagename", False, 24, ["latest"])
        self.list_tags_mock.assert_called_with(
            "imagename"
        )
        self.list_tags_mock.assert_called_with("imagename")
        self.get_tag_config_mock.assert_called_with("imagename", "image")
        delete_tags_patched.assert_called_with(
            self.registry, "imagename", False, ["image"], ["latest"])

    @patch('registry.delete_tags')
    def test_delete_tags_by_age_dry_run(self, delete_tags_patched):
        delete_tags_by_age(self.registry, "imagename", True, 24, ["latest"])
        self.list_tags_mock.assert_called_with(
            "imagename"
        )
        self.list_tags_mock.assert_called_with("imagename")
        self.get_tag_config_mock.assert_called_with("imagename", "image")
        delete_tags_patched.assert_called_with(
            self.registry, "imagename", True, ["image"], ["latest"])


class TestArgParser(unittest.TestCase):

    def test_no_args(self):
        with self.assertRaises(SystemExit):
            parse_args("")

    def test_all_args(self):
        args_list = ["-r", "hostname",
                     "-l", "loginstring",
                     "-d",
                     "-n", "15",
                     "--dry-run",
                     "-i", "imagename1", "imagename2",
                     "--keep-tags", "keep1", "keep2",
                     "--tags-like", "tags_like_text",
                     "--no-validate-ssl",
                     "--delete-all",
                     "--layers",
                     "--delete-by-hours", "24"]
        args = parse_args(args_list)
        self.assertTrue(args.delete)
        self.assertTrue(args.layers)
        self.assertTrue(args.no_validate_ssl)
        self.assertTrue(args.delete_all)
        self.assertTrue(args.layers)
        self.assertEqual(args.image, ["imagename1", "imagename2"])
        self.assertEqual(args.num, "15")
        self.assertEqual(args.login, "loginstring")
        self.assertEqual(args.tags_like, ["tags_like_text"])
        self.assertEqual(args.host, "hostname")
        self.assertEqual(args.keep_tags, ["keep1", "keep2"])
        self.assertEqual(args.delete_by_hours, "24")


if __name__ == '__main__':
    unittest.main()
