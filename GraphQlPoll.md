# Poll GraphQl

## Mutaatiot

### Example mutation
```graphql
mutation @device(uuid: "4922d7d7-956f-40d0-803f-7d06a0c75d40", token: "500a6615-6ddf-4f79-a391-efcf89d33422") {
  pollEnrollToSurvey(surveyId: 8, backQuestionAnswers: "{\"x\":5,\"y\":6}", feelingQuestionAnswers: "{\"x\":5,\"y\":6}")  {
    ok
  }
}
```
### Example answer
```graphql
{
  "data": {
    "pollEnrollToSurvey": {
      "ok": true
    }
  }
}
```

### Enable/disable survey on machine
enableSurvey

### Enable/disable survey on machine
enableCarbon

### Add survey. Chk timeline.
//days: User survey days
//startDay: Survey start day
//endDay: Survey end day
///description: Survey description
///maxBackQuestion: Amount of different survey questions, default 3
pollAddSurvey

### Add user to survey. Select randomly survey days to user
//surveyId: Id of survey, where to take part.
///backQuestionAnswers: User answers to back question on JSON form
///feelingQuestionAnswers: User answer to feeling questions on JSON form
pollEnrollToSurvey

### Add trip to user. User trip times needs to be unigue. Returns trip Id.
//startTime: Trip start time
//endTime: Trip end time
//surveyId: Survey Id
///purpose: Trip purpose (tyo, opiskelu, tyoasia, vapaaaika, ostos, muu) Default empty
///startMunicipality: Trip start municiability (Tampere, Kangasala, Lempaala, Nokia, Orivesi, Pirkkala, Vesilahti, Ylojarvi, muu) Default Tampere
///endMunicipality: Trip end municiability (Tampere, Kangasala, Lempaala, Nokia, Orivesi, Pirkkala, Vesilahti, Ylojarvi, muu) Default Tampere
pollAddTrip

### Add leg of the trip. Leg times need to be unigue. Trip needs to be unapproved.
//tripId: Trip Id
//startTime: Leg start time
//endTime: Leg end time
///tripLength: Lengt of the trip
///transportMode: Transport mode of the trip
///nrPassengers: Amount of passengers
///startLoc: Leg start location
///endLoc: Leg end location
///carbonFootprint: Leg carbon footprint
pollAddLeg

### Update given information to trip. Trip times needs to be unigue. Its not possible to approve unpurpose or empty trip.
//tripId: Trip Id
//surveyId: Survey Id
///startTime: Trip start time
///endTime: Trip end time
///purpose: Trip purpose (tyo, opiskelu, tyoasia, vapaaaika, ostos, muu)
///startMunicipality: Trip start municiability (Tampere, Kangasala, Lempaala, Nokia, Orivesi, Pirkkala, Vesilahti, Ylojarvi, muu)
///endMunicipality: Trip start municiability (Tampere, Kangasala, Lempaala, Nokia, Orivesi, Pirkkala, Vesilahti, Ylojarvi, muu)
///approved: Approved (True/False)
pollEditTrip

### Mark user day ready. Chk that all day trip has purpose and leg.
//selectedDate: Selected day
//surveyId: Survey Id
pollMarkUserDayReady

### Mark user survey ready. Chk that all day has been approved.
//surveyId: Survey Id
pollApproveUserSurvey

### Register user to lottery.
//name: Name
//email: Email
pollEnrollLottery

### Add empty question set in JSON form to database
//description: Description
//question: Question in JSON form
//questionType: Question type (background, feeling, somethingelse)
///surveyId: Survey Id, where Question belongs
pollAddQuestion

### Add locations to leg. Chk time of the leg.
//loc: Loc point
//legId: Leg Id
//time: Point time
pollLocationToLeg

### Delete trip. Only unapproved trip can be deleted.
//tripId: Trip Id
//surveyId: Survey Id
pollDelTrip

### Delete leg from the trip. Only leg from unapproved trip can be deleted.
//tripId: Trip Id
//legId: Leg Id
//surveyId: Survey Id
pollDelLeg

### Compine two trip to one. Only unapproved trip can be compine.
//tripId: First trip Id
//trip2Id: Second trip Id
//surveyId: Survey Id
pollJoinTrip

### Split one trip to two. Only unapproved trip can be split.
//tripId: Trip Id
//afterLegId: Last leg of first trip.
//surveyId: Survey Id
pollSplitTrip

### Saves user answers to question.
//surveyId: Survey Id
///backQuestionAnswers: User answers to back question on JSON form
///feelingQuestionAnswers: User answer to feeling questions on JSON form
pollAddUserAnswerToQuestions

## Queryt

### Example query
```graphql
query @device(uuid: "4922d7d7-956f-40d0-803f-7d06a0c75d40", token: "469443b1-6929-49bb-87c9-3aafea7b83f5"){
	pollSurveyInfo  {
    		startDay
    		endDay
    		days
    		maxBackQuestion
    		description
  }
}
```
### Example answer
```graphql
{
  "data": {
    "pollSurveyInfo": [
      {
        "startDay": "2023-08-14",
        "endDay": "2023-08-16",
        "days": 3,
        "maxBackQuestion": 3,
        "description": "kokeilu"
      },
      {
        "startDay": "2023-07-04",
        "endDay": "2023-07-07",
        "days": 3,
        "maxBackQuestion": 3,
        "description": "kokeilu2"
      }
    ]
  }
}
```

### Return surveys.
pollSurveyInfo

### Return user survey info.
///surveyId: Survey Id
pollUserSurvey

### Returns empty base questions.
//questionType: Question type(background, feeling, somethingelse)
///surveyId: Survey Id
pollSurveyQuestions

### Return selected base question.
//questionId
pollSurveyQuestion.

### Return user trips form selected day.
//day: Selected day
///surveyId: Survey Id
pollDayTrips

### Return trip legs.
//tripId: Trip Id
pollTripsLegs

### Device information
///id
///uuid
///token
///platform
///systemVersion
///brand
///model
///surveyEnabled
///mocafEnabled
///friendlyName
///debugLogLevel
///debuggingEnabledAt
///customConfig
///accountKey
///healthImpactEnabled
///enabledAt
///disabledAt
///createdAt
///lastProcessedDataReceivedAt
///trips
///partisipantsSet
deviceData
