import React from "react";
import ReactDOM from "react-dom";
import * as Sentry from "@sentry/browser";
import { ApolloClient, InMemoryCache, ApolloProvider, } from "@apollo/client";
import cubejs from '@cubejs-client/core';
import { CubeProvider } from '@cubejs-client/react';
import { App } from "./App";


let apolloClient;
let cubejsApi;

function initializeApp(container, { graphqlUrl, cubeUrl, sentryDSN }) {
  if (!apolloClient) {
    apolloClient = new ApolloClient({
      uri: graphqlUrl,
      cache: new InMemoryCache()
    });
  }
  if (!cubejsApi) {
    cubejsApi = cubejs('', {
      apiUrl: cubeUrl,
    });
  }
  if (sentryDSN) {
    Sentry.init({ dsn: sentryDSN });
  }
  ReactDOM.render((
    <ApolloProvider client={apolloClient}>
      <CubeProvider cubejsApi={cubejsApi}>
        <App />
      </CubeProvider>
    </ApolloProvider>
  ), container);
}

window.initializeApp = initializeApp;
